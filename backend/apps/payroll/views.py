"""Viewsets for the payroll module (spec §9.10).

Compensation data is sensitive: payroll periods, records and components
are confined to ``payroll.view`` / ``payroll.manage`` holders. Employees
never see raw records — they access their own published ``Payslip``
records through ``PayslipViewSet`` (secure payslip access).
"""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.permissions import HasTenant
from apps.common.viewsets import TenantModelViewSet
from apps.employees.models import Employee
from apps.reports.exporters import export_report
from apps.reports.registry import ReportResult

from . import services
from .models import (
    PayComponent,
    PayrollLine,
    PayrollPeriod,
    PayrollRecord,
    Payslip,
)
from .serializers import (
    PayComponentSerializer,
    PayrollLineSerializer,
    PayrollPeriodSerializer,
    PayrollRecordListSerializer,
    PayrollRecordSerializer,
    PayslipSerializer,
)


def _own_employee(request) -> Employee | None:
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


class PayrollPeriodViewSet(TenantModelViewSet):
    """Payroll periods and their run lifecycle."""

    queryset = PayrollPeriod.objects.select_related("approved_by")
    serializer_class = PayrollPeriodSerializer
    permission_required = {
        "default": "payroll.view",
        "create": "payroll.manage",
        "update": "payroll.manage",
        "partial_update": "payroll.manage",
        "destroy": "payroll.manage",
        "generate_records": "payroll.manage",
        "approve": "payroll.manage",
        "mark_paid": "payroll.manage",
        "generate_payslips": "payroll.manage",
        "publish_payslips": "payroll.manage",
    }
    search_fields = ["name", "code"]
    filterset_fields = ["status"]
    ordering_fields = ["start_date", "created_at"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE, "payroll.period", entity_id=serializer.instance.pk,
            description=f"Created payroll period {serializer.instance.code}",
        )

    @action(detail=True, methods=["post"], url_path="generate-records")
    def generate_records(self, request, pk=None):
        """Generate a draft payroll record for every active employee."""
        period = self.get_object()
        created = services.generate_records(period)
        record_audit(
            AuditAction.UPDATE, "payroll.period", entity_id=period.pk,
            description=f"Generated {created} payroll record(s) for {period.code}",
        )
        return Response(
            PayrollPeriodSerializer(period, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve the period — locks and approves its records."""
        period = self.get_object()
        services.approve_period(period, user=request.user)
        record_audit(
            AuditAction.APPROVE, "payroll.period", entity_id=period.pk,
            description=f"Approved payroll period {period.code}",
        )
        return Response(
            PayrollPeriodSerializer(period, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        """Mark an approved period as paid."""
        period = self.get_object()
        services.mark_period_paid(period)
        record_audit(
            AuditAction.PAYMENT, "payroll.period", entity_id=period.pk,
            description=f"Marked payroll period {period.code} paid",
        )
        return Response(
            PayrollPeriodSerializer(period, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="generate-payslips")
    def generate_payslips(self, request, pk=None):
        """Generate (unpublished) payslips for every record in the period."""
        period = self.get_object()
        count = 0
        for rec in period.records.select_related("employee", "period"):
            services.generate_payslip(rec)
            count += 1
        return Response({"period": period.code, "payslips_generated": count})

    @action(detail=True, methods=["post"], url_path="publish-payslips")
    def publish_payslips(self, request, pk=None):
        """Publish every generated payslip in the period and notify employees."""
        period = self.get_object()
        count = 0
        for payslip in period.payslips.select_related(
            "employee", "period", "record"
        ).filter(is_published=False):
            services.publish_payslip(payslip)
            count += 1
        record_audit(
            AuditAction.UPDATE, "payroll.period", entity_id=period.pk,
            description=f"Published {count} payslip(s) for {period.code}",
        )
        return Response({"period": period.code, "payslips_published": count})

    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        """Export the period's payroll as CSV or XLSX."""
        period = self.get_object()
        # Use ?fmt= — `?format=` is reserved by DRF content negotiation.
        fmt = (request.query_params.get("fmt") or "csv").lower()
        if fmt not in {"csv", "xlsx"}:
            fmt = "csv"
        columns, rows = services.export_rows(period)
        record_audit(
            AuditAction.EXPORT, "payroll.period", entity_id=period.pk,
            description=f"Exported payroll period {period.code} as {fmt.upper()}",
        )
        return export_report(
            ReportResult(columns=columns, rows=rows), fmt, f"payroll_{period.code}"
        )


class PayComponentViewSet(TenantModelViewSet):
    """Configurable allowance / deduction definitions."""

    queryset = PayComponent.objects.all()
    serializer_class = PayComponentSerializer
    permission_required = {
        "create": "payroll.manage",
        "update": "payroll.manage",
        "partial_update": "payroll.manage",
        "destroy": "payroll.manage",
    }
    search_fields = ["name", "code"]
    filterset_fields = ["component_type", "is_active"]


class PayrollRecordViewSet(TenantModelViewSet):
    """Per-employee payroll records — restricted to payroll roles."""

    queryset = PayrollRecord.objects.select_related(
        "employee", "period"
    ).prefetch_related("lines")
    permission_required = {
        "default": "payroll.view",
        "create": "payroll.manage",
        "update": "payroll.manage",
        "partial_update": "payroll.manage",
        "destroy": "payroll.manage",
        "recalculate": "payroll.manage",
    }
    filterset_fields = ["period", "employee", "status"]
    ordering_fields = ["created_at", "net_pay"]

    def get_serializer_class(self):
        if self.action == "list":
            return PayrollRecordListSerializer
        return PayrollRecordSerializer

    def perform_update(self, serializer):
        record = serializer.save()
        # Editable inputs (overtime, basic salary) changed — recompute totals.
        services.recalculate_record(record)

    @action(detail=True, methods=["post"])
    def recalculate(self, request, pk=None):
        """Recompute the record's totals, leave-without-pay and gross / net."""
        record = self.get_object()
        services.recalculate_record(record)
        return Response(
            PayrollRecordSerializer(record, context={"request": request}).data
        )


class PayrollLineViewSet(TenantModelViewSet):
    """Allowance / deduction lines on payroll records."""

    queryset = PayrollLine.objects.select_related("record", "component")
    serializer_class = PayrollLineSerializer
    permission_required = {
        "default": "payroll.view",
        "create": "payroll.manage",
        "update": "payroll.manage",
        "partial_update": "payroll.manage",
        "destroy": "payroll.manage",
    }
    filterset_fields = ["record", "line_type"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        services.recalculate_record(serializer.instance.record)

    def perform_update(self, serializer):
        serializer.save()
        services.recalculate_record(serializer.instance.record)

    def perform_destroy(self, instance):
        record = instance.record
        super().perform_destroy(instance)
        services.recalculate_record(record)


class PayslipViewSet(viewsets.ReadOnlyModelViewSet):
    """Secure payslip access.

    Employees see only their own *published* payslips; payroll roles see
    every payslip in the tenant.
    """

    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated, HasTenant]
    filterset_fields = ["period", "employee", "is_published"]
    ordering_fields = ["created_at"]

    def _can_manage_payroll(self) -> bool:
        tenant = getattr(self.request, "tenant", None)
        user = self.request.user
        return user.has_perm_code("payroll.view", tenant) or user.has_perm_code(
            "payroll.manage", tenant
        )

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        queryset = Payslip.objects.filter(tenant=tenant).select_related(
            "employee", "period", "record"
        )
        if self._can_manage_payroll():
            return queryset
        own = _own_employee(self.request)
        if own is None:
            return queryset.none()
        return queryset.filter(employee=own, is_published=True)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish a single payslip and notify the employee."""
        if not request.user.has_perm_code(
            "payroll.manage", getattr(request, "tenant", None)
        ):
            raise PermissionDenied("Publishing a payslip requires payroll.manage.")
        payslip = self.get_object()
        services.publish_payslip(payslip)
        record_audit(
            AuditAction.UPDATE, "payroll.payslip", entity_id=payslip.pk,
            description=f"Published payslip {payslip.reference}",
        )
        return Response(
            PayslipSerializer(payslip, context={"request": request}).data
        )

    @action(detail=False, url_path="my-payslips")
    def my_payslips(self, request):
        """The requesting user's own published payslips."""
        own = _own_employee(request)
        if own is None:
            raise NotFound("You do not have an employee profile in this organisation.")
        queryset = Payslip.objects.filter(
            tenant=getattr(request, "tenant", None),
            employee=own,
            is_published=True,
        ).select_related("period", "record")
        page = self.paginate_queryset(queryset)
        serializer = PayslipSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
