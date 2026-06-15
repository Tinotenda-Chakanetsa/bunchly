"""Viewsets for the recruitment / ATS module (spec §9.5).

Recruitment data is confined to ``recruitment.view`` (read) and
``recruitment.manage`` (write) holders. The one exception is the job
posting ``announcements`` action — open to any tenant member so
internal vacancies are visible org-wide.
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.viewsets import TenantModelViewSet
from apps.employees.serializers import EmployeeSerializer

from . import services
from .enums import PostingStatus, RequisitionStatus
from .models import (
    Candidate,
    CandidateDocument,
    Interview,
    JobPosting,
    JobRequisition,
    Offer,
)
from .serializers import (
    CandidateDocumentSerializer,
    CandidateListSerializer,
    CandidateSerializer,
    InterviewScoreSerializer,
    InterviewSerializer,
    JobPostingPublicSerializer,
    JobPostingSerializer,
    JobRequisitionSerializer,
    OfferSerializer,
    StageSerializer,
)

_WRITE = {
    "create": "recruitment.manage",
    "update": "recruitment.manage",
    "partial_update": "recruitment.manage",
    "destroy": "recruitment.manage",
}


class JobRequisitionViewSet(TenantModelViewSet):
    """Requests to hire."""

    queryset = JobRequisition.objects.select_related(
        "department", "job_title", "grade", "hiring_manager"
    )
    serializer_class = JobRequisitionSerializer
    permission_required = {"default": "recruitment.view", "approve": "recruitment.manage", **_WRITE}
    search_fields = ["reference", "title"]
    filterset_fields = ["status", "department"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        instance = serializer.save(
            tenant=self.get_tenant(),
            reference=services.generate_requisition_reference(self.get_tenant()),
        )
        record_audit(
            AuditAction.CREATE, "recruitment.requisition", entity_id=instance.pk,
            description=f"Created job requisition {instance.reference}",
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a job requisition so it can be posted."""
        from django.utils import timezone

        requisition = self.get_object()
        if requisition.status not in {
            RequisitionStatus.DRAFT, RequisitionStatus.ON_HOLD,
        }:
            raise ValidationError("Only a draft or on-hold requisition can be approved.")
        requisition.status = RequisitionStatus.APPROVED
        requisition.approved_by = request.user
        requisition.approved_at = timezone.now()
        requisition.save(update_fields=[
            "status", "approved_by", "approved_at", "updated_at",
        ])
        record_audit(
            AuditAction.APPROVE, "recruitment.requisition", entity_id=requisition.pk,
            description=f"Approved job requisition {requisition.reference}",
        )
        return Response(
            JobRequisitionSerializer(requisition, context={"request": request}).data
        )


class JobPostingViewSet(TenantModelViewSet):
    """Job postings, including internal vacancy announcements."""

    queryset = JobPosting.objects.select_related("requisition", "location")
    serializer_class = JobPostingSerializer
    permission_required = {
        "default": "recruitment.view",
        "announcements": None,  # open to every tenant member
        **_WRITE,
    }
    search_fields = ["title", "description"]
    filterset_fields = ["status", "is_internal", "employment_type"]
    ordering_fields = ["posted_date", "closing_date", "created_at"]

    @action(detail=False)
    def announcements(self, request):
        """Open internal vacancy announcements — visible to all employees."""
        postings = self.get_queryset().filter(
            status=PostingStatus.OPEN, is_internal=True
        )
        page = self.paginate_queryset(postings)
        serializer = JobPostingPublicSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class CandidateViewSet(TenantModelViewSet):
    """Candidates and their pipeline progression."""

    queryset = Candidate.objects.select_related(
        "posting", "linked_employee"
    ).prefetch_related("documents", "interviews", "offer")
    permission_required = {
        "default": "recruitment.view",
        "advance": "recruitment.manage",
        "convert": "recruitment.manage",
        **_WRITE,
    }
    search_fields = ["first_name", "last_name", "email"]
    filterset_fields = ["posting", "stage"]
    ordering_fields = ["created_at", "rating", "applied_at"]

    def get_serializer_class(self):
        return CandidateListSerializer if self.action == "list" else CandidateSerializer

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        """Move a candidate to a new pipeline stage."""
        candidate = self.get_object()
        payload = StageSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        stage = payload.validated_data["stage"]
        services.advance_candidate(candidate, stage)
        if stage == "rejected" and payload.validated_data.get("reason"):
            services.reject_candidate(
                candidate, reason=payload.validated_data["reason"]
            )
        record_audit(
            AuditAction.UPDATE, "recruitment.candidate", entity_id=candidate.pk,
            description=f"Moved {candidate.full_name} to stage '{candidate.stage}'",
        )
        return Response(
            CandidateSerializer(candidate, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Convert a hired candidate into an employee record."""
        candidate = self.get_object()
        employee = services.convert_to_employee(candidate, user=request.user)
        record_audit(
            AuditAction.CREATE, "employees.employee", entity_id=employee.pk,
            description=f"Converted candidate {candidate.full_name} to employee "
                        f"{employee.employee_number}",
        )
        return Response(
            {
                "candidate": str(candidate.pk),
                "employee": EmployeeSerializer(
                    employee, context={"request": request}
                ).data,
            },
            status=201,
        )


class CandidateDocumentViewSet(TenantModelViewSet):
    """Documents uploaded for candidates (CV, certificates, references)."""

    queryset = CandidateDocument.objects.select_related("candidate")
    serializer_class = CandidateDocumentSerializer
    permission_required = {"default": "recruitment.view", **_WRITE}
    filterset_fields = ["candidate", "doc_type"]


class InterviewViewSet(TenantModelViewSet):
    """Interview scheduling and scoring."""

    queryset = Interview.objects.select_related("candidate").prefetch_related(
        "interviewers"
    )
    serializer_class = InterviewSerializer
    permission_required = {
        "default": "recruitment.view",
        "score": "recruitment.manage",
        **_WRITE,
    }
    filterset_fields = ["candidate", "status", "mode"]
    ordering_fields = ["scheduled_at", "created_at"]

    @action(detail=True, methods=["post"])
    def score(self, request, pk=None):
        """Record an interview's score and feedback, marking it completed."""
        from .enums import InterviewStatus

        interview = self.get_object()
        payload = InterviewScoreSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        interview.score = payload.validated_data["score"]
        interview.feedback = payload.validated_data.get("feedback", "")
        interview.status = InterviewStatus.COMPLETED
        interview.save(update_fields=["score", "feedback", "status", "updated_at"])
        return Response(
            InterviewSerializer(interview, context={"request": request}).data
        )


class OfferViewSet(TenantModelViewSet):
    """Offers and their approval / acceptance lifecycle."""

    queryset = Offer.objects.select_related("candidate", "approved_by")
    serializer_class = OfferSerializer
    permission_required = {
        "default": "recruitment.view",
        "submit": "recruitment.manage",
        "approve": "recruitment.manage",
        "send": "recruitment.manage",
        "accept": "recruitment.manage",
        "decline": "recruitment.manage",
        "withdraw": "recruitment.manage",
        **_WRITE,
    }
    filterset_fields = ["status", "candidate"]
    ordering_fields = ["created_at"]

    def _respond(self, offer):
        return Response(
            OfferSerializer(offer, context={"request": self.request}).data
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit a draft offer for approval."""
        return self._respond(services.submit_offer(self.get_object()))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve an offer pending approval."""
        offer = services.approve_offer(self.get_object(), user=request.user)
        record_audit(
            AuditAction.APPROVE, "recruitment.offer", entity_id=offer.pk,
            description=f"Approved offer for {offer.candidate.full_name}",
        )
        return self._respond(offer)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Mark an approved offer as sent to the candidate."""
        return self._respond(services.send_offer(self.get_object()))

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Record candidate acceptance — the candidate becomes hired."""
        offer = services.accept_offer(self.get_object())
        record_audit(
            AuditAction.UPDATE, "recruitment.offer", entity_id=offer.pk,
            description=f"Offer accepted by {offer.candidate.full_name}",
        )
        return self._respond(offer)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        """Record candidate declining a sent offer."""
        return self._respond(services.decline_offer(self.get_object()))

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        """Withdraw an offer before it is accepted or declined."""
        return self._respond(services.withdraw_offer(self.get_object()))
