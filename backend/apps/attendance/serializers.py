"""Serializers for the time & attendance module (spec §9.9)."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .enums import AttendanceStatus
from .models import AttendanceRecord, Shift, Timesheet


class ShiftSerializer(TenantScopedModelSerializer):
    """A configurable working pattern."""

    scheduled_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Shift
        fields = [
            "id", "name", "code", "description", "start_time", "end_time",
            "break_minutes", "grace_in_minutes", "grace_out_minutes",
            "is_active", "scheduled_minutes", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_code(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = Shift.all_objects.filter(tenant=tenant, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A shift with this code already exists."
            )
        return value


class AttendanceRecordSerializer(TenantScopedModelSerializer):
    """Read representation of one working day — all figures are derived."""

    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    entry_type_display = serializers.CharField(
        source="get_entry_type_display", read_only=True
    )
    approval_status_display = serializers.CharField(
        source="get_approval_status_display", read_only=True
    )
    is_exception = serializers.BooleanField(read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id", "employee", "employee_name", "timesheet", "shift",
            "shift_name", "work_date", "entry_type", "entry_type_display",
            "status", "status_display", "clock_in", "clock_out",
            "break_minutes", "worked_minutes", "overtime_minutes",
            "is_late", "late_minutes", "is_early_departure",
            "early_departure_minutes", "approval_status",
            "approval_status_display", "is_exception", "decided_by",
            "decided_at", "notes", "created_at", "updated_at",
        ]
        # Every field is service-managed; writes go through the actions.
        read_only_fields = fields


class ManualEntrySerializer(serializers.Serializer):
    """Input for creating a manual attendance record."""

    employee = serializers.UUIDField(required=False, allow_null=True)
    work_date = serializers.DateField()
    shift = serializers.UUIDField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT
    )
    clock_in = serializers.DateTimeField(required=False, allow_null=True)
    clock_out = serializers.DateTimeField(required=False, allow_null=True)
    break_minutes = serializers.IntegerField(required=False, min_value=0, default=0)
    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )


class ClockInSerializer(serializers.Serializer):
    """Input for clocking in — an optional shift and timestamp."""

    shift = serializers.UUIDField(required=False, allow_null=True)
    when = serializers.DateTimeField(required=False, allow_null=True)


class ClockOutSerializer(serializers.Serializer):
    """Input for clocking out — an optional timestamp."""

    when = serializers.DateTimeField(required=False, allow_null=True)


class DecisionSerializer(serializers.Serializer):
    """Input for an approve / reject action."""

    note = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )


class TimesheetSerializer(TenantScopedModelSerializer):
    """A per-employee attendance period with aggregated totals."""

    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    totals = serializers.SerializerMethodField()

    class Meta:
        model = Timesheet
        fields = [
            "id", "employee", "employee_name", "period_start", "period_end",
            "status", "status_display", "submitted_at", "decided_by",
            "decided_at", "decision_note", "exported_at", "notes", "totals",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "status", "submitted_at", "decided_by", "decided_at",
            "decision_note", "exported_at", "created_at", "updated_at",
        ]

    def get_totals(self, obj) -> dict:
        from . import services

        return services.timesheet_totals(obj)
