"""Serializers for the benefits-administration module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import BenefitEnrolmentHistory, BenefitType, EmployeeBenefit


class BenefitTypeSerializer(TenantScopedModelSerializer):
    """A configurable benefit definition."""

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    enrolment_count = serializers.IntegerField(
        source="enrolments.count", read_only=True
    )

    class Meta:
        model = BenefitType
        fields = [
            "id", "name", "code", "category", "category_display",
            "description", "provider", "contribution_basis",
            "employee_contribution", "employer_contribution", "is_taxable",
            "requires_approval", "covers_dependants", "eligibility_min_months",
            "eligible_employment_statuses", "pay_component", "is_active",
            "enrolment_count", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_code(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = BenefitType.all_objects.filter(tenant=tenant, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A benefit type with this code already exists."
            )
        return value


class BenefitEnrolmentHistorySerializer(serializers.ModelSerializer):
    """An entry in an enrolment's history log (read-only)."""

    event_display = serializers.CharField(source="get_event_display", read_only=True)
    actor_name = serializers.CharField(
        source="actor.full_name", read_only=True, default=None
    )

    class Meta:
        model = BenefitEnrolmentHistory
        fields = [
            "id", "event", "event_display", "note", "actor", "actor_name",
            "created_at",
        ]
        read_only_fields = fields


class EmployeeBenefitSerializer(TenantScopedModelSerializer):
    """An employee's benefit enrolment with its history."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    benefit_type_name = serializers.CharField(
        source="benefit_type.name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    history = BenefitEnrolmentHistorySerializer(many=True, read_only=True)

    class Meta:
        model = EmployeeBenefit
        fields = [
            "id", "employee", "employee_name", "benefit_type",
            "benefit_type_name", "status", "status_display", "start_date",
            "end_date", "employee_contribution", "employer_contribution",
            "covered_dependants", "notes", "approved_by", "approved_at",
            "history", "created_at", "updated_at",
        ]
        # Enrolment is created via the `enrol` flow; contributions are
        # snapshotted by the service and status/dates by the lifecycle
        # actions. Updates may only change notes / covered dependants.
        read_only_fields = [
            "employee", "benefit_type", "status", "start_date", "end_date",
            "employee_contribution", "employer_contribution", "approved_by",
            "approved_at", "created_at", "updated_at",
        ]


class EmployeeBenefitListSerializer(serializers.ModelSerializer):
    """Lightweight enrolment row."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    benefit_type_name = serializers.CharField(
        source="benefit_type.name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = EmployeeBenefit
        fields = [
            "id", "employee", "employee_name", "benefit_type",
            "benefit_type_name", "status", "status_display", "start_date",
            "employee_contribution", "employer_contribution",
        ]


class EnrolSerializer(serializers.Serializer):
    """Input for creating an enrolment."""

    employee = serializers.UUIDField(required=False)
    benefit_type = serializers.UUIDField()
    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )


class EnrolmentNoteSerializer(serializers.Serializer):
    """Optional note for a decline / suspend / terminate decision."""

    note = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )
