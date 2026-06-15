"""Serializers for the leave & absence module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import LeaveApproval, LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(TenantScopedModelSerializer):
    """A configurable leave category and its rules."""

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )

    class Meta:
        model = LeaveType
        fields = [
            "id", "name", "code", "category", "category_display", "description",
            "colour", "is_paid", "default_annual_days", "accrual_method",
            "allow_carry_forward", "max_carry_forward_days", "requires_approval",
            "requires_hr_confirmation", "extra_approval_stage",
            "extra_approval_label", "notify_finance", "requires_documentation",
            "min_notice_days", "max_consecutive_days", "allow_negative_balance",
            "gender_eligibility", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_code(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = LeaveType.all_objects.filter(tenant=tenant, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A leave type with this code already exists."
            )
        return value


class LeaveBalanceSerializer(TenantScopedModelSerializer):
    """An employee's balance for one leave type in one year."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    entitlement_total = serializers.DecimalField(
        max_digits=7, decimal_places=2, read_only=True
    )
    available_days = serializers.DecimalField(
        max_digits=7, decimal_places=2, read_only=True
    )

    class Meta:
        model = LeaveBalance
        fields = [
            "id", "employee", "employee_name", "leave_type", "leave_type_name",
            "leave_type_code", "year", "entitled_days", "carried_forward_days",
            "taken_days", "pending_days", "adjustment_days", "adjustment_reason",
            "entitlement_total", "available_days", "created_at", "updated_at",
        ]
        # taken/pending are workflow-managed; never set directly via the API.
        read_only_fields = [
            "taken_days", "pending_days", "created_at", "updated_at",
        ]


class LeaveApprovalSerializer(serializers.ModelSerializer):
    """One stage of a request's approval chain (read-only)."""

    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    decided_by_name = serializers.CharField(
        source="decided_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = LeaveApproval
        fields = [
            "id", "stage", "stage_display", "sequence", "label", "status",
            "status_display", "decided_by", "decided_by_name", "decided_at",
            "comments",
        ]
        read_only_fields = fields


class LeaveRequestSerializer(TenantScopedModelSerializer):
    """A leave application with its computed cost and approval chain."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_colour = serializers.CharField(
        source="leave_type.colour", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    current_stage_display = serializers.CharField(
        source="get_current_stage_display", read_only=True, default=None
    )
    approvals = LeaveApprovalSerializer(many=True, read_only=True)
    is_editable = serializers.BooleanField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "employee", "employee_name", "leave_type", "leave_type_name",
            "leave_type_code", "leave_type_colour", "start_date", "end_date",
            "start_portion", "end_portion", "total_days", "reason",
            "contact_during_leave", "supporting_document", "status",
            "status_display", "current_stage", "current_stage_display",
            "submitted_at", "decided_at", "decision_note", "approvals",
            "is_editable", "created_at", "updated_at",
        ]
        # Workflow-owned fields — moved only by the lifecycle actions.
        read_only_fields = [
            "total_days", "status", "current_stage", "submitted_at",
            "decided_at", "decision_note", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be before the start date."}
            )
        return attrs


class LeaveRequestListSerializer(serializers.ModelSerializer):
    """Lightweight row for request lists and calendars."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    leave_type_colour = serializers.CharField(
        source="leave_type.colour", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "employee", "employee_name", "leave_type", "leave_type_name",
            "leave_type_colour", "start_date", "end_date", "total_days",
            "status", "status_display", "current_stage",
        ]


class LeaveDecisionSerializer(serializers.Serializer):
    """Input for an approve/reject decision."""

    comments = serializers.CharField(
        required=False, allow_blank=True, max_length=2000
    )


class LeaveBalanceAdjustSerializer(serializers.Serializer):
    """Input for an HR balance adjustment."""

    adjustment_days = serializers.DecimalField(max_digits=7, decimal_places=2)
    reason = serializers.CharField(max_length=255)
