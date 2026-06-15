"""Serializers for the recruitment / ATS module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import (
    Candidate,
    CandidateDocument,
    Interview,
    JobPosting,
    JobRequisition,
    Offer,
)


class JobRequisitionSerializer(TenantScopedModelSerializer):
    """A request to hire."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    department_name = serializers.CharField(
        source="department.name", read_only=True, default=None
    )

    class Meta:
        model = JobRequisition
        fields = [
            "id", "reference", "title", "department", "department_name",
            "job_title", "grade", "headcount", "employment_type",
            "hiring_manager", "status", "status_display", "reason",
            "approved_by", "approved_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "reference", "status", "approved_by", "approved_at",
            "created_at", "updated_at",
        ]


class JobPostingSerializer(TenantScopedModelSerializer):
    """A published job advert."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    location_name = serializers.CharField(
        source="location.name", read_only=True, default=None
    )
    candidate_count = serializers.IntegerField(
        source="candidates.count", read_only=True
    )

    class Meta:
        model = JobPosting
        fields = [
            "id", "requisition", "title", "description", "location",
            "location_name", "employment_type", "is_internal", "status",
            "status_display", "posted_date", "closing_date",
            "candidate_count", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class JobPostingPublicSerializer(serializers.ModelSerializer):
    """A trimmed posting view for internal vacancy announcements."""

    location_name = serializers.CharField(
        source="location.name", read_only=True, default=None
    )

    class Meta:
        model = JobPosting
        fields = [
            "id", "title", "description", "location_name", "employment_type",
            "posted_date", "closing_date",
        ]
        read_only_fields = fields


class CandidateDocumentSerializer(TenantScopedModelSerializer):
    """A document uploaded for a candidate."""

    class Meta:
        model = CandidateDocument
        fields = [
            "id", "candidate", "doc_type", "file", "description", "created_at",
        ]
        read_only_fields = ["created_at"]


class InterviewSerializer(TenantScopedModelSerializer):
    """A scheduled interview."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    candidate_name = serializers.CharField(
        source="candidate.full_name", read_only=True
    )

    class Meta:
        model = Interview
        fields = [
            "id", "candidate", "candidate_name", "scheduled_at", "mode",
            "location", "interviewers", "status", "status_display", "score",
            "feedback", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class OfferSerializer(TenantScopedModelSerializer):
    """An offer extended to a candidate."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    candidate_name = serializers.CharField(
        source="candidate.full_name", read_only=True
    )

    class Meta:
        model = Offer
        fields = [
            "id", "candidate", "candidate_name", "job_title", "salary",
            "currency", "employment_type", "start_date", "expiry_date",
            "status", "status_display", "notes", "approved_by", "approved_at",
            "sent_at", "decided_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "status", "approved_by", "approved_at", "sent_at", "decided_at",
            "created_at", "updated_at",
        ]


class CandidateSerializer(TenantScopedModelSerializer):
    """A full candidate record with documents, interviews and offer."""

    full_name = serializers.CharField(read_only=True)
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    posting_title = serializers.CharField(source="posting.title", read_only=True)
    documents = CandidateDocumentSerializer(many=True, read_only=True)
    interviews = InterviewSerializer(many=True, read_only=True)
    offer = OfferSerializer(read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id", "posting", "posting_title", "first_name", "last_name",
            "full_name", "email", "phone", "source", "stage", "stage_display",
            "rating", "summary", "notes", "rejection_reason", "applied_at",
            "linked_employee", "documents", "interviews", "offer",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "stage", "rejection_reason", "linked_employee",
            "created_at", "updated_at",
        ]


class CandidateListSerializer(serializers.ModelSerializer):
    """Lightweight candidate row for pipeline lists."""

    full_name = serializers.CharField(read_only=True)
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    posting_title = serializers.CharField(source="posting.title", read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id", "posting", "posting_title", "full_name", "email", "stage",
            "stage_display", "rating", "applied_at", "created_at",
        ]


class StageSerializer(serializers.Serializer):
    """Input for advancing a candidate's pipeline stage."""

    stage = serializers.CharField()
    reason = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )


class InterviewScoreSerializer(serializers.Serializer):
    """Input for recording an interview score."""

    score = serializers.IntegerField(min_value=1, max_value=5)
    feedback = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )
