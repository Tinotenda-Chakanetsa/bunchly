"""Time & attendance models (spec §9.9).

``Shift``             a configurable working pattern (start / end / break).
``Timesheet``         a per-employee period that groups attendance records
                      and is submitted / approved as a unit, then exported
                      to payroll.
``AttendanceRecord``  one working day for an employee — clock in / out or a
                      manual entry, carrying lateness, early-departure and
                      overtime figures and (for manual entries) its own
                      approval state.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import (
    ApprovalStatus,
    AttendanceStatus,
    EntryType,
    TimesheetStatus,
)

# Hours expected on a working day when an employee has no assigned shift.
DEFAULT_DAY_MINUTES = 480


class Shift(TenantOwnedModel):
    """A configurable working pattern (spec §9.9 — shift management)."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    description = models.CharField(max_length=255, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(default=0)
    # Minutes of grace before a clock-in counts as late / a clock-out as
    # an early departure.
    grace_in_minutes = models.PositiveIntegerField(default=0)
    grace_out_minutes = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_shift_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    @property
    def scheduled_minutes(self) -> int:
        """Paid minutes in the shift — span minus the unpaid break.

        Handles an overnight shift (``end_time`` <= ``start_time``).
        """
        base = datetime(2000, 1, 1)
        start = base.replace(
            hour=self.start_time.hour, minute=self.start_time.minute
        )
        end = base.replace(hour=self.end_time.hour, minute=self.end_time.minute)
        if end <= start:
            end += timedelta(days=1)
        span = int((end - start).total_seconds() // 60)
        return max(span - self.break_minutes, 0)


class Timesheet(TenantOwnedModel):
    """A per-employee attendance period, submitted and approved as a unit."""

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="timesheets"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(
        max_length=12,
        choices=TimesheetStatus.choices,
        default=TimesheetStatus.DRAFT,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    exported_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-period_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "employee", "period_start", "period_end"],
                name="uniq_timesheet_period_per_employee",
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "employee", "status"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} {self.period_start}–{self.period_end}"


class AttendanceRecord(TenantOwnedModel):
    """One working day for an employee (spec §9.9 — clock in/out, exceptions)."""

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    timesheet = models.ForeignKey(
        Timesheet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="records",
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )
    work_date = models.DateField(db_index=True)
    entry_type = models.CharField(
        max_length=8, choices=EntryType.choices, default=EntryType.CLOCK
    )
    status = models.CharField(
        max_length=10,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT,
        db_index=True,
    )
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    break_minutes = models.PositiveIntegerField(default=0)
    # Derived figures — recomputed by the service whenever times change.
    worked_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    is_late = models.BooleanField(default=False)
    late_minutes = models.PositiveIntegerField(default=0)
    is_early_departure = models.BooleanField(default=False)
    early_departure_minutes = models.PositiveIntegerField(default=0)
    # Manual entries start pending; clock entries are auto-approved.
    approval_status = models.CharField(
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,
        db_index=True,
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-work_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "employee", "work_date"],
                name="uniq_attendance_per_employee_per_day",
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "employee", "work_date"]),
            models.Index(fields=["tenant", "work_date", "status"]),
            models.Index(fields=["tenant", "approval_status"]),
            models.Index(fields=["tenant", "timesheet"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} — {self.work_date} ({self.get_status_display()})"

    @property
    def is_exception(self) -> bool:
        """True when the day needs HR/manager attention."""
        return (
            self.is_late
            or self.is_early_departure
            or self.status == AttendanceStatus.ABSENT
            or self.approval_status == ApprovalStatus.PENDING
        )
