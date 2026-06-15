"""Viewsets for the time & attendance module (spec §9.9).

Visibility scoping (as in the leave / performance modules):
- ``attendance.manage`` -> sees & manages all attendance in the tenant.
- ``attendance.view``   -> sees all attendance (read-only reporting roles).
- otherwise             -> sees own records, plus direct reports' records
                           when the caller holds ``employees.view_team``.

Shift definitions are configured by ``attendance.manage`` holders and are
readable by every tenant member (the clock-in widget needs them).
"""
from __future__ import annotations

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.viewsets import TenantModelViewSet
from apps.employees.models import Employee
from apps.reports.exporters import export_report
from apps.reports.registry import ReportResult

from . import services
from .enums import TimesheetStatus
from .models import AttendanceRecord, Shift, Timesheet
from .serializers import (
    AttendanceRecordSerializer,
    ClockInSerializer,
    ClockOutSerializer,
    DecisionSerializer,
    ManualEntrySerializer,
    ShiftSerializer,
    TimesheetSerializer,
)

_WRITE = {
    "create": "attendance.manage",
    "update": "attendance.manage",
    "partial_update": "attendance.manage",
    "destroy": "attendance.manage",
}


def _own_employee(request) -> Employee | None:
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


def _has(request, code: str) -> bool:
    return request.user.has_perm_code(code, getattr(request, "tenant", None))


def _visible_employee_ids(request) -> list | None:
    """Employee ids the caller may see, or ``None`` for unrestricted."""
    if _has(request, "attendance.manage") or _has(request, "attendance.view"):
        return None
    own = _own_employee(request)
    if own is None:
        return []
    ids = [own.id]
    if _has(request, "employees.view_team"):
        tenant = getattr(request, "tenant", None)
        ids += list(
            Employee.objects.filter(tenant=tenant, line_manager=own)
            .values_list("id", flat=True)
        )
    return ids


def _resolve_employee(request, employee_id) -> Employee:
    """Resolve an employee id within the tenant or raise a 400."""
    employee = Employee.objects.filter(
        tenant=getattr(request, "tenant", None), pk=employee_id
    ).first()
    if employee is None:
        raise ValidationError({"employee": "Employee not found."})
    return employee


def _resolve_shift(request, shift_id) -> Shift | None:
    if not shift_id:
        return None
    shift = Shift.objects.filter(
        tenant=getattr(request, "tenant", None), pk=shift_id
    ).first()
    if shift is None:
        raise ValidationError({"shift": "Shift not found."})
    return shift


class ShiftViewSet(TenantModelViewSet):
    """Configurable working patterns. Read-open; writes need manage."""

    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_required = {**_WRITE}
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE, "attendance.shift",
            entity_id=serializer.instance.pk,
            description=f"Created shift {serializer.instance.code}",
        )


class AttendanceRecordViewSet(TenantModelViewSet):
    """Daily attendance — clock in / out, manual entries and approvals."""

    queryset = AttendanceRecord.objects.select_related(
        "employee", "shift", "timesheet", "decided_by"
    )
    serializer_class = AttendanceRecordSerializer
    permission_required = {
        "update": "attendance.manage",
        "partial_update": "attendance.manage",
        "destroy": "attendance.manage",
    }
    filterset_fields = ["employee", "status", "approval_status", "entry_type"]
    search_fields = ["employee__first_name", "employee__last_name"]
    ordering_fields = ["work_date", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        visible = _visible_employee_ids(self.request)
        if visible is None:
            return queryset
        return queryset.filter(employee_id__in=visible)

    def _can_review(self, employee) -> bool:
        """True when the caller may approve/reject ``employee``'s records."""
        if _has(self.request, "attendance.manage"):
            return True
        own = _own_employee(self.request)
        return own is not None and employee.line_manager_id == own.id

    def create(self, request, *args, **kwargs):
        """Create a manual attendance entry.

        An employee may record a manual entry for themselves; an
        ``attendance.manage`` holder may record one for anyone (and it is
        auto-approved). Either way it goes through the service so the
        derived figures stay consistent.
        """
        payload = ManualEntrySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        can_manage = _has(request, "attendance.manage")

        if data.get("employee") and can_manage:
            employee = _resolve_employee(request, data["employee"])
        else:
            employee = _own_employee(request)
            if employee is None:
                raise NotFound(
                    "You do not have an employee profile in this organisation."
                )
            if data.get("employee") and str(employee.pk) != str(data["employee"]):
                raise PermissionDenied(
                    "You may only record manual entries for yourself."
                )

        record = services.record_manual_entry(
            tenant=getattr(request, "tenant", None),
            employee=employee,
            work_date=data["work_date"],
            shift=_resolve_shift(request, data.get("shift")),
            clock_in=data.get("clock_in"),
            clock_out=data.get("clock_out"),
            break_minutes=data.get("break_minutes", 0),
            status=data["status"],
            notes=data.get("notes", ""),
            auto_approve=can_manage,
        )
        record_audit(
            AuditAction.CREATE, "attendance.record", entity_id=record.pk,
            description=f"Manual attendance entry for {employee} on "
                        f"{record.work_date}",
        )
        return Response(
            AttendanceRecordSerializer(record, context={"request": request}).data,
            status=201,
        )

    @action(detail=False, methods=["post"], url_path="clock-in")
    def clock_in(self, request):
        """Clock the requesting user in for today."""
        employee = _own_employee(request)
        if employee is None:
            raise NotFound(
                "You do not have an employee profile in this organisation."
            )
        payload = ClockInSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        record = services.clock_in(
            tenant=getattr(request, "tenant", None),
            employee=employee,
            shift=_resolve_shift(request, payload.validated_data.get("shift")),
            when=payload.validated_data.get("when"),
        )
        record_audit(
            AuditAction.CREATE, "attendance.record", entity_id=record.pk,
            description=f"{employee} clocked in",
        )
        return Response(
            AttendanceRecordSerializer(record, context={"request": request}).data
        )

    @action(detail=False, methods=["post"], url_path="clock-out")
    def clock_out(self, request):
        """Clock the requesting user out of today's open record."""
        employee = _own_employee(request)
        if employee is None:
            raise NotFound(
                "You do not have an employee profile in this organisation."
            )
        payload = ClockOutSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        record = AttendanceRecord.objects.filter(
            tenant=getattr(request, "tenant", None),
            employee=employee,
            work_date=timezone.localdate(),
        ).first()
        if record is None or record.clock_in is None:
            raise ValidationError("You have not clocked in today.")
        services.clock_out(record, when=payload.validated_data.get("when"))
        record_audit(
            AuditAction.UPDATE, "attendance.record", entity_id=record.pk,
            description=f"{employee} clocked out",
        )
        return Response(
            AttendanceRecordSerializer(record, context={"request": request}).data
        )

    @action(detail=False)
    def today(self, request):
        """The requesting user's record for today, plus the active shifts."""
        employee = _own_employee(request)
        if employee is None:
            raise NotFound(
                "You do not have an employee profile in this organisation."
            )
        record = AttendanceRecord.objects.filter(
            tenant=getattr(request, "tenant", None),
            employee=employee,
            work_date=timezone.localdate(),
        ).select_related("shift").first()
        shifts = Shift.objects.filter(
            tenant=getattr(request, "tenant", None), is_active=True
        )
        return Response({
            "record": (
                AttendanceRecordSerializer(
                    record, context={"request": request}
                ).data
                if record else None
            ),
            "shifts": ShiftSerializer(
                shifts, many=True, context={"request": request}
            ).data,
        })

    @action(detail=False, url_path="my-records")
    def my_records(self, request):
        """The requesting user's own attendance records."""
        employee = _own_employee(request)
        if employee is None:
            raise NotFound(
                "You do not have an employee profile in this organisation."
            )
        queryset = self.filter_queryset(
            super().get_queryset().filter(employee=employee)
        )
        page = self.paginate_queryset(queryset)
        serializer = AttendanceRecordSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=False)
    def exceptions(self, request):
        """Records needing attention — late, early, absent or unapproved."""
        queryset = services.attendance_exceptions(
            self.filter_queryset(self.get_queryset())
        )
        page = self.paginate_queryset(queryset)
        serializer = AttendanceRecordSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a pending manual attendance record."""
        record = self.get_object()
        if not self._can_review(record.employee):
            raise PermissionDenied(
                "You may only review records for your direct reports."
            )
        payload = DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.decide_record(
            record, approved=True, user=request.user,
            note=payload.validated_data.get("note", ""),
        )
        record_audit(
            AuditAction.APPROVE, "attendance.record", entity_id=record.pk,
            description=f"Approved attendance record for {record.employee}",
        )
        return Response(
            AttendanceRecordSerializer(record, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a pending manual attendance record."""
        record = self.get_object()
        if not self._can_review(record.employee):
            raise PermissionDenied(
                "You may only review records for your direct reports."
            )
        payload = DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.decide_record(
            record, approved=False, user=request.user,
            note=payload.validated_data.get("note", ""),
        )
        record_audit(
            AuditAction.REJECT, "attendance.record", entity_id=record.pk,
            description=f"Rejected attendance record for {record.employee}",
        )
        return Response(
            AttendanceRecordSerializer(record, context={"request": request}).data
        )


class TimesheetViewSet(TenantModelViewSet):
    """Per-employee timesheet periods and their approval lifecycle."""

    queryset = Timesheet.objects.select_related("employee", "decided_by")
    serializer_class = TimesheetSerializer
    permission_required = {
        "update": "attendance.manage",
        "partial_update": "attendance.manage",
        "destroy": "attendance.manage",
    }
    filterset_fields = ["employee", "status"]
    ordering_fields = ["period_start", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        visible = _visible_employee_ids(self.request)
        if visible is None:
            return queryset
        return queryset.filter(employee_id__in=visible)

    def _can_review(self, employee) -> bool:
        if _has(self.request, "attendance.manage"):
            return True
        own = _own_employee(self.request)
        return own is not None and employee.line_manager_id == own.id

    def create(self, request, *args, **kwargs):
        """Open a timesheet. Employees open their own; managers may open
        one for any employee they manage."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.validated_data.get("employee")
        own = _own_employee(request)
        if not _has(request, "attendance.manage"):
            if own is None:
                raise NotFound(
                    "You do not have an employee profile in this organisation."
                )
            if employee is not None and employee.id != own.id:
                raise PermissionDenied(
                    "You may only open a timesheet for yourself."
                )
            employee = own
        if employee is None:
            raise ValidationError({"employee": "This field is required."})

        timesheet = services.get_or_create_timesheet(
            tenant=getattr(request, "tenant", None),
            employee=employee,
            period_start=serializer.validated_data["period_start"],
            period_end=serializer.validated_data["period_end"],
        )
        return Response(
            TimesheetSerializer(timesheet, context={"request": request}).data,
            status=201,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit a draft timesheet for manager approval."""
        timesheet = self.get_object()
        own = _own_employee(request)
        if not _has(request, "attendance.manage"):
            if own is None or timesheet.employee_id != own.id:
                raise PermissionDenied(
                    "You may only submit your own timesheet."
                )
        services.submit_timesheet(timesheet)
        record_audit(
            AuditAction.SUBMIT, "attendance.timesheet", entity_id=timesheet.pk,
            description=f"Submitted timesheet for {timesheet.employee}",
        )
        return Response(
            TimesheetSerializer(timesheet, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a submitted timesheet."""
        timesheet = self.get_object()
        if not self._can_review(timesheet.employee):
            raise PermissionDenied(
                "You may only review timesheets for your direct reports."
            )
        payload = DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.decide_timesheet(
            timesheet, approved=True, user=request.user,
            note=payload.validated_data.get("note", ""),
        )
        record_audit(
            AuditAction.APPROVE, "attendance.timesheet", entity_id=timesheet.pk,
            description=f"Approved timesheet for {timesheet.employee}",
        )
        return Response(
            TimesheetSerializer(timesheet, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a submitted timesheet."""
        timesheet = self.get_object()
        if not self._can_review(timesheet.employee):
            raise PermissionDenied(
                "You may only review timesheets for your direct reports."
            )
        payload = DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.decide_timesheet(
            timesheet, approved=False, user=request.user,
            note=payload.validated_data.get("note", ""),
        )
        record_audit(
            AuditAction.REJECT, "attendance.timesheet", entity_id=timesheet.pk,
            description=f"Rejected timesheet for {timesheet.employee}",
        )
        return Response(
            TimesheetSerializer(timesheet, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="mark-exported")
    def mark_exported(self, request, pk=None):
        """Flag an approved timesheet as exported to payroll."""
        if not _has(request, "attendance.manage"):
            raise PermissionDenied(
                "You do not have permission to export timesheets."
            )
        timesheet = self.get_object()
        services.mark_exported(timesheet)
        record_audit(
            AuditAction.EXPORT, "attendance.timesheet", entity_id=timesheet.pk,
            description=f"Marked timesheet for {timesheet.employee} exported",
        )
        return Response(
            TimesheetSerializer(timesheet, context={"request": request}).data
        )

    @action(detail=True)
    def records(self, request, pk=None):
        """The attendance records linked to this timesheet."""
        timesheet = self.get_object()
        queryset = timesheet.records.select_related(
            "employee", "shift"
        ).order_by("work_date")
        serializer = AttendanceRecordSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=True)
    def export(self, request, pk=None):
        """Export the timesheet's records as CSV or XLSX (for payroll)."""
        timesheet = self.get_object()
        # Use ?fmt= — `?format=` is reserved by DRF content negotiation.
        fmt = (request.query_params.get("fmt") or "csv").lower()
        if fmt not in {"csv", "xlsx"}:
            fmt = "csv"
        columns, rows = services.export_rows(timesheet)
        record_audit(
            AuditAction.EXPORT, "attendance.timesheet", entity_id=timesheet.pk,
            description=f"Exported timesheet for {timesheet.employee} "
                        f"as {fmt.upper()}",
        )
        return export_report(
            ReportResult(columns=columns, rows=rows),
            fmt,
            f"timesheet_{timesheet.period_start}",
        )

    @action(detail=False, url_path="my-timesheets")
    def my_timesheets(self, request):
        """The requesting user's own timesheets."""
        employee = _own_employee(request)
        if employee is None:
            raise NotFound(
                "You do not have an employee profile in this organisation."
            )
        queryset = self.filter_queryset(
            super().get_queryset().filter(employee=employee)
        )
        page = self.paginate_queryset(queryset)
        serializer = TimesheetSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=False, url_path="pending-approvals")
    def pending_approvals(self, request):
        """Submitted timesheets the caller is entitled to review."""
        queryset = self.filter_queryset(
            self.get_queryset().filter(status=TimesheetStatus.SUBMITTED)
        )
        if not _has(request, "attendance.manage"):
            own = _own_employee(request)
            queryset = (
                queryset.filter(employee__line_manager=own)
                if own else queryset.none()
            )
        page = self.paginate_queryset(queryset)
        serializer = TimesheetSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)
