"""Viewsets for the education-assistance module (spec §9.12).

Access scoping:
- ``education.view_all_claims`` -> sees every claim / dependant.
- ``education.review_claim``    -> HR: sees claims and dependants to review.
- otherwise                     -> sees only their own claims / dependants.

Financial detail visibility is governed by the queryset scoping above —
plain employees only ever see their own claims.
"""
from __future__ import annotations

from datetime import date

from django.db.models import Count, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.permissions import HasModulePermission, HasTenant
from apps.common.viewsets import TenantModelViewSet
from apps.employees.models import Employee

from . import services
from .enums import ClaimStatus
from .models import (
    Dependant,
    EducationBenefitRule,
    EducationClaim,
    EducationClaimApproval,
    EducationClaimDocument,
)
from .serializers import (
    ClaimNoteSerializer,
    DependantSerializer,
    EducationBenefitRuleSerializer,
    EducationClaimApprovalSerializer,
    EducationClaimDocumentSerializer,
    EducationClaimListSerializer,
    EducationClaimSerializer,
    HrApproveSerializer,
    HrRejectSerializer,
    MarkPaidSerializer,
)


def _own_employee(request) -> Employee | None:
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


def _has(request, code: str) -> bool:
    return request.user.has_perm_code(code, getattr(request, "tenant", None))


class EducationBenefitRuleViewSet(TenantModelViewSet):
    """The eligibility-rules engine. Reading is open; configuring is gated."""

    queryset = EducationBenefitRule.objects.all()
    serializer_class = EducationBenefitRuleSerializer
    permission_required = {
        "create": "education.configure",
        "update": "education.configure",
        "partial_update": "education.configure",
        "destroy": "education.configure",
    }
    filterset_fields = ["is_active"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE, "education.benefit_rule",
            entity_id=serializer.instance.pk,
            description="Created education benefit rule",
        )

    def perform_update(self, serializer):
        serializer.save()
        record_audit(
            AuditAction.UPDATE, "education.benefit_rule",
            entity_id=serializer.instance.pk,
            description="Updated education benefit rule",
        )


class DependantViewSet(TenantModelViewSet):
    """Employee dependants — employees manage their own; HR sees all."""

    queryset = Dependant.objects.select_related("employee")
    serializer_class = DependantSerializer
    filterset_fields = ["employee", "is_benefit_eligible", "education_level"]
    search_fields = ["full_name", "institution_name"]

    def _is_hr(self) -> bool:
        return _has(self.request, "education.view_all_claims") or _has(
            self.request, "education.review_claim"
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self._is_hr():
            return queryset
        own = _own_employee(self.request)
        return queryset.filter(employee=own) if own else queryset.none()

    def perform_create(self, serializer):
        request = self.request
        tenant = getattr(request, "tenant", None)
        target = serializer.validated_data.get("employee")
        own = _own_employee(request)
        if not self._is_hr():
            if own is None or target != own:
                raise PermissionDenied(
                    "You may only register your own dependants."
                )
        # Enforce the configured maximum number of eligible children.
        if serializer.validated_data.get("is_benefit_eligible", True):
            rule = services.get_active_rule(tenant)
            services.validate_dependant_capacity(target, rule)
        instance = serializer.save(tenant=tenant)
        record_audit(
            AuditAction.CREATE, "education.dependant", entity_id=instance.pk,
            description=f"Registered dependant {instance.full_name}",
        )

    def perform_update(self, serializer):
        if not self._is_hr():
            own = _own_employee(self.request)
            if own is None or serializer.instance.employee_id != own.id:
                raise PermissionDenied("You may only edit your own dependants.")
        serializer.save()


class EducationClaimViewSet(TenantModelViewSet):
    """Education-assistance claims — submission and the HR/Finance workflow."""

    queryset = EducationClaim.objects.select_related(
        "employee", "dependant", "hr_reviewed_by", "paid_by"
    ).prefetch_related("documents", "approvals")
    permission_required = {"create": "education.submit_claim"}
    filterset_fields = ["status", "employee", "education_level", "period_type"]
    search_fields = ["reference", "academic_period", "institution_name"]
    ordering_fields = ["created_at", "submitted_at", "amount_claimed"]

    def get_serializer_class(self):
        if self.action == "list":
            return EducationClaimListSerializer
        return EducationClaimSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if _has(self.request, "education.view_all_claims"):
            return queryset
        own = _own_employee(self.request)
        return queryset.filter(employee=own) if own else queryset.none()

    def perform_create(self, serializer):
        request = self.request
        tenant = getattr(request, "tenant", None)
        target = serializer.validated_data.get("employee")
        own = _own_employee(request)
        is_hr = _has(request, "education.view_all_claims")
        if not is_hr:
            if own is None:
                raise ValidationError(
                    {"employee": "You do not have an employee profile."}
                )
            target = own
        elif target is None:
            target = own
        dependant = serializer.validated_data.get("dependant")
        if dependant is not None and dependant.employee_id != getattr(
            target, "id", None
        ):
            raise ValidationError(
                {"dependant": "The dependant must belong to the claiming employee."}
            )
        instance = serializer.save(
            tenant=tenant,
            employee=target,
            reference=services.generate_reference(tenant),
            status=ClaimStatus.DRAFT,
        )
        record_audit(
            AuditAction.CREATE, "education.claim", entity_id=instance.pk,
            description=f"Drafted education claim {instance.reference}",
        )

    # --- helpers ----------------------------------------------------------
    def _respond(self, claim):
        return Response(
            EducationClaimSerializer(claim, context={"request": self.request}).data
        )

    def _require(self, code: str):
        if not _has(self.request, code):
            raise PermissionDenied(
                f"This action requires the '{code}' permission."
            )

    def _require_owner(self, claim):
        own = _own_employee(self.request)
        if (own is None or claim.employee_id != own.id) and not _has(
            self.request, "education.view_all_claims"
        ):
            raise PermissionDenied("You may only act on your own claim.")

    # --- lifecycle actions ------------------------------------------------
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit a draft claim for HR review."""
        claim = self.get_object()
        self._require_owner(claim)
        services.submit_claim(claim)
        record_audit(
            AuditAction.SUBMIT, "education.claim", entity_id=claim.pk,
            description=f"Submitted education claim {claim.reference}",
        )
        return self._respond(claim)

    @action(detail=True, methods=["post"], url_path="hr-approve")
    def hr_approve(self, request, pk=None):
        """HR approves the claim and routes it to Finance."""
        self._require("education.review_claim")
        claim = self.get_object()
        payload = HrApproveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.hr_approve(
            claim, user=request.user,
            amount_approved=payload.validated_data.get("amount_approved"),
            note=payload.validated_data.get("note", ""),
        )
        record_audit(
            AuditAction.APPROVE, "education.claim", entity_id=claim.pk,
            description=f"HR approved education claim {claim.reference}",
        )
        return self._respond(claim)

    @action(detail=True, methods=["post"], url_path="hr-reject")
    def hr_reject(self, request, pk=None):
        """HR rejects the claim with a reason."""
        self._require("education.review_claim")
        claim = self.get_object()
        payload = HrRejectSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        reason = payload.validated_data["reason"]
        services.hr_reject(claim, user=request.user, reason=reason)
        record_audit(
            AuditAction.REJECT, "education.claim", entity_id=claim.pk,
            description=f"HR rejected education claim {claim.reference}",
            reason=reason,
        )
        return self._respond(claim)

    @action(detail=True, methods=["post"], url_path="request-info")
    def request_info(self, request, pk=None):
        """HR returns the claim to the employee for more information."""
        self._require("education.review_claim")
        claim = self.get_object()
        payload = ClaimNoteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.hr_request_info(
            claim, user=request.user, note=payload.validated_data["note"]
        )
        return self._respond(claim)

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        """Finance records payment of an HR-approved claim."""
        self._require("education.pay_claim")
        claim = self.get_object()
        payload = MarkPaidSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.mark_paid(
            claim, user=request.user,
            payment_reference=payload.validated_data["payment_reference"],
            note=payload.validated_data.get("note", ""),
        )
        record_audit(
            AuditAction.PAYMENT, "education.claim", entity_id=claim.pk,
            description=f"Recorded payment for education claim {claim.reference}",
        )
        return self._respond(claim)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a claim that has not yet been paid."""
        claim = self.get_object()
        self._require_owner(claim)
        services.cancel_claim(claim)
        record_audit(
            AuditAction.UPDATE, "education.claim", entity_id=claim.pk,
            description=f"Cancelled education claim {claim.reference}",
        )
        return self._respond(claim)

    @action(detail=False, url_path="my-claims")
    def my_claims(self, request):
        """The requesting user's own education claims."""
        own = _own_employee(request)
        if own is None:
            raise NotFound("You do not have an employee profile in this organisation.")
        queryset = self.filter_queryset(self.get_queryset().filter(employee=own))
        page = self.paginate_queryset(queryset)
        serializer = EducationClaimListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, url_path="pending-hr")
    def pending_hr(self, request):
        """Claims awaiting HR review."""
        self._require("education.review_claim")
        queryset = self.filter_queryset(
            self.get_queryset().filter(status=ClaimStatus.SUBMITTED)
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            EducationClaimListSerializer(page, many=True).data
        )

    @action(detail=False, url_path="pending-payment")
    def pending_payment(self, request):
        """Claims approved by HR and awaiting Finance payment."""
        self._require("education.pay_claim")
        queryset = self.filter_queryset(
            self.get_queryset().filter(status=ClaimStatus.HR_APPROVED)
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(
            EducationClaimListSerializer(page, many=True).data
        )


class EducationClaimDocumentViewSet(TenantModelViewSet):
    """Supporting documents for education claims."""

    queryset = EducationClaimDocument.objects.select_related("claim")
    serializer_class = EducationClaimDocumentSerializer
    filterset_fields = ["claim", "doc_type"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if _has(self.request, "education.view_all_claims") or _has(
            self.request, "education.review_claim"
        ):
            return queryset
        own = _own_employee(self.request)
        return queryset.filter(claim__employee=own) if own else queryset.none()

    def perform_create(self, serializer):
        claim = serializer.validated_data["claim"]
        own = _own_employee(self.request)
        is_hr = _has(self.request, "education.view_all_claims") or _has(
            self.request, "education.review_claim"
        )
        if not is_hr and (own is None or claim.employee_id != own.id):
            raise PermissionDenied(
                "You may only attach documents to your own claim."
            )
        serializer.save(
            tenant=getattr(self.request, "tenant", None),
            uploaded_by=self.request.user,
        )


class EducationClaimApprovalViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only decision log for education claims."""

    serializer_class = EducationClaimApprovalSerializer
    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "education.view_all_claims"
    filterset_fields = ["claim", "stage", "decision"]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        return EducationClaimApproval.objects.filter(tenant=tenant).select_related(
            "claim", "actor"
        )


class EducationDashboardView(APIView):
    """Education-assistance dashboard metrics (spec §9.12 F)."""

    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "education.view_all_claims"

    def get(self, request):
        tenant = getattr(request, "tenant", None)
        year = date.today().year
        claims = EducationClaim.objects.filter(tenant=tenant)
        year_claims = claims.filter(created_at__year=year)
        paid = claims.filter(status=ClaimStatus.PAID, paid_at__year=year)

        by_department = list(
            paid.values("employee__department__name")
            .annotate(total=Sum("amount_approved"), count=Count("id"))
            .order_by("-total")
        )
        by_level = list(
            paid.values("education_level")
            .annotate(total=Sum("amount_approved"), count=Count("id"))
            .order_by("-total")
        )
        rule = services.get_active_rule(tenant)
        exceeding = 0
        if rule and rule.max_amount_per_child:
            exceeding = claims.filter(
                amount_claimed__gt=rule.max_amount_per_child
            ).count()

        return Response({
            "year": year,
            "total_claims_year": year_claims.count(),
            "total_paid_year": paid.aggregate(t=Sum("amount_approved"))["t"] or 0,
            "pending_hr": claims.filter(status=ClaimStatus.SUBMITTED).count(),
            "pending_payment": claims.filter(
                status=ClaimStatus.HR_APPROVED
            ).count(),
            "rejected_claims": year_claims.filter(
                status=ClaimStatus.REJECTED
            ).count(),
            "claims_exceeding_limit": exceeding,
            "cost_per_department": [
                {
                    "department": d["employee__department__name"] or "(Unassigned)",
                    "total": d["total"] or 0,
                    "count": d["count"],
                }
                for d in by_department
            ],
            "cost_per_level": [
                {
                    "education_level": d["education_level"],
                    "total": d["total"] or 0,
                    "count": d["count"],
                }
                for d in by_level
            ],
        })
