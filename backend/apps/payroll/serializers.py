"""Serializers for the payroll module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import (
    PayComponent,
    PayrollLine,
    PayrollPeriod,
    PayrollRecord,
    Payslip,
)


class PayrollPeriodSerializer(TenantScopedModelSerializer):
    """A pay run period."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    record_count = serializers.IntegerField(source="records.count", read_only=True)

    class Meta:
        model = PayrollPeriod
        fields = [
            "id", "name", "code", "start_date", "end_date", "pay_date",
            "status", "status_display", "notes", "approved_by", "approved_at",
            "record_count", "created_at", "updated_at",
        ]
        read_only_fields = [
            "status", "approved_by", "approved_at", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be before the start date."}
            )
        return attrs

    def validate_code(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = PayrollPeriod.all_objects.filter(tenant=tenant, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A payroll period with this code already exists."
            )
        return value


class PayComponentSerializer(TenantScopedModelSerializer):
    """A configurable allowance / deduction definition."""

    component_type_display = serializers.CharField(
        source="get_component_type_display", read_only=True
    )

    class Meta:
        model = PayComponent
        fields = [
            "id", "name", "code", "component_type", "component_type_display",
            "is_taxable", "default_amount", "description", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PayrollLineSerializer(TenantScopedModelSerializer):
    """An allowance / deduction line on a payroll record."""

    class Meta:
        model = PayrollLine
        fields = [
            "id", "record", "component", "line_type", "description",
            "amount", "is_taxable", "created_at",
        ]
        read_only_fields = ["created_at"]


class PayrollRecordSerializer(serializers.ModelSerializer):
    """A full payroll record with its allowance / deduction lines."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    lines = PayrollLineSerializer(many=True, read_only=True)

    class Meta:
        model = PayrollRecord
        fields = [
            "id", "period", "period_name", "employee", "employee_name",
            "currency", "basic_salary", "total_allowances", "total_deductions",
            "overtime_amount", "leave_without_pay_days",
            "leave_without_pay_amount", "gross_pay", "net_pay", "status",
            "status_display", "notes", "lines", "created_at", "updated_at",
        ]
        # Computed totals are owned by services.recalculate_record.
        read_only_fields = [
            "total_allowances", "total_deductions", "leave_without_pay_days",
            "leave_without_pay_amount", "gross_pay", "net_pay", "status",
            "created_at", "updated_at",
        ]


class PayrollRecordListSerializer(serializers.ModelSerializer):
    """Lightweight payroll record row."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PayrollRecord
        fields = [
            "id", "period", "employee", "employee_name", "currency",
            "basic_salary", "gross_pay", "net_pay", "status", "status_display",
        ]


class PayslipSerializer(serializers.ModelSerializer):
    """An employee-visible payslip."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    period_name = serializers.CharField(source="period.name", read_only=True)

    class Meta:
        model = Payslip
        fields = [
            "id", "record", "employee", "employee_name", "period",
            "period_name", "reference", "is_published", "published_at",
            "snapshot", "created_at",
        ]
        read_only_fields = fields
