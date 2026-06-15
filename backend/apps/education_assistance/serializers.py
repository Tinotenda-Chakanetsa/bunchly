"""Serializers for the education-assistance module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import (
    Dependant,
    EducationBenefitRule,
    EducationClaim,
    EducationClaimApproval,
    EducationClaimDocument,
)


class EducationBenefitRuleSerializer(TenantScopedModelSerializer):
    """The configurable eligibility-rules engine."""

    class Meta:
        model = EducationBenefitRule
        fields = [
            "id", "name", "max_children", "covered_levels",
            "max_amount_per_child", "currency", "frequency",
            "eligible_employment_statuses", "require_probation_passed",
            "max_child_age", "max_claims_per_period", "required_documents",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class DependantSerializer(TenantScopedModelSerializer):
    """An employee's registered child / ward."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    relationship_display = serializers.CharField(
        source="get_relationship_display", read_only=True
    )

    class Meta:
        model = Dependant
        fields = [
            "id", "employee", "employee_name", "full_name", "date_of_birth",
            "relationship", "relationship_display", "education_level",
            "institution_name", "student_number", "birth_certificate",
            "is_benefit_eligible", "eligibility_override_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class EducationClaimDocumentSerializer(TenantScopedModelSerializer):
    """A supporting document on a claim."""

    doc_type_display = serializers.CharField(
        source="get_doc_type_display", read_only=True
    )

    class Meta:
        model = EducationClaimDocument
        fields = [
            "id", "claim", "doc_type", "doc_type_display", "file",
            "description", "uploaded_by", "created_at",
        ]
        read_only_fields = ["uploaded_by", "created_at"]


class EducationClaimApprovalSerializer(serializers.ModelSerializer):
    """An entry in a claim's decision log (read-only)."""

    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    decision_display = serializers.CharField(
        source="get_decision_display", read_only=True
    )
    actor_name = serializers.CharField(
        source="actor.full_name", read_only=True, default=None
    )

    class Meta:
        model = EducationClaimApproval
        fields = [
            "id", "stage", "stage_display", "decision", "decision_display",
            "actor", "actor_name", "comment", "created_at",
        ]
        read_only_fields = fields


class EducationClaimSerializer(TenantScopedModelSerializer):
    """A full education-assistance claim with documents and decision log."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    dependant_name = serializers.CharField(
        source="dependant.full_name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payable_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    documents = EducationClaimDocumentSerializer(many=True, read_only=True)
    approvals = EducationClaimApprovalSerializer(many=True, read_only=True)

    class Meta:
        model = EducationClaim
        fields = [
            "id", "reference", "employee", "employee_name", "dependant",
            "dependant_name", "academic_period", "period_type",
            "education_level", "institution_name", "amount_claimed",
            "amount_approved", "payable_amount", "currency", "status",
            "status_display", "submitted_at", "hr_reviewed_by",
            "hr_reviewed_at", "hr_note", "rejection_reason",
            "payment_reference", "paid_by", "paid_at", "payment_note",
            "documents", "approvals", "created_at", "updated_at",
        ]
        read_only_fields = [
            "reference", "amount_approved", "status", "submitted_at",
            "hr_reviewed_by", "hr_reviewed_at", "hr_note", "rejection_reason",
            "payment_reference", "paid_by", "paid_at", "payment_note",
            "created_at", "updated_at",
        ]


class EducationClaimListSerializer(serializers.ModelSerializer):
    """Lightweight claim row for lists and queues."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    dependant_name = serializers.CharField(
        source="dependant.full_name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = EducationClaim
        fields = [
            "id", "reference", "employee", "employee_name", "dependant_name",
            "academic_period", "education_level", "amount_claimed",
            "amount_approved", "currency", "status", "status_display",
            "created_at",
        ]


class HrApproveSerializer(serializers.Serializer):
    """Input for an HR approval decision."""

    amount_approved = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    note = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )


class HrRejectSerializer(serializers.Serializer):
    """Input for an HR rejection."""

    reason = serializers.CharField(max_length=255)


class ClaimNoteSerializer(serializers.Serializer):
    """Input for a request-more-information decision."""

    note = serializers.CharField(max_length=255)


class MarkPaidSerializer(serializers.Serializer):
    """Input for a Finance payment record."""

    payment_reference = serializers.CharField(max_length=80)
    note = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )
