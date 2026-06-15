"""Time & attendance business logic (spec §9.9).

All derived figures on an ``AttendanceRecord`` — worked minutes, overtime,
lateness and early departure — are computed here by ``recalculate_record``
so the model never stores a stale total. Clocking, manual entries, the
record-approval flow and the timesheet lifecycle (submit → approve →
export to payroll) are the rest of the surface.
"""
from __future__ import annotations

from datetime import datetime

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .enums import (
    NON_WORKING_STATUSES,
    ApprovalStatus,
    AttendanceStatus,
    EntryType,
    TimesheetStatus,
)
from .models import DEFAULT_DAY_MINUTES, AttendanceRecord, Shift, Timesheet


# --- helpers ---------------------------------------------------------------

def _minutes_between(start: datetime, end: datetime) -> int:
    """Whole minutes from ``start`` to ``end``; rolls a negative span over
    midnight (an overnight shift) by adding 24 hours."""
    delta = int((end - start).total_seconds() // 60)
    if delta < 0:
        delta += 24 * 60
    return delta


def _expected_clock_in(record: AttendanceRecord) -> datetime | None:
    """The shift start as an aware datetime on the record's work date."""
    if record.shift is None:
        return None
    naive = datetime.combine(record.work_date, record.shift.start_time)
    return timezone.make_aware(naive, timezone.get_current_timezone())


def _expected_clock_out(record: AttendanceRecord) -> datetime | None:
    """The shift end as an aware datetime on the record's work date."""
    if record.shift is None:
        return None
    naive = datetime.combine(record.work_date, record.shift.end_time)
    out = timezone.make_aware(naive, timezone.get_current_timezone())
    expected_in = _expected_clock_in(record)
    if expected_in is not None and out <= expected_in:
        out += timezone.timedelta(days=1)  # overnight shift
    return out


def recalculate_record(record: AttendanceRecord) -> AttendanceRecord:
    """Recompute worked minutes, overtime, lateness and early departure.

    Does not save — callers persist the record after adjusting it.
    """
    # Reset derived fields; a non-working day has no figures at all.
    record.worked_minutes = 0
    record.overtime_minutes = 0
    record.is_late = False
    record.late_minutes = 0
    record.is_early_departure = False
    record.early_departure_minutes = 0

    if record.status in NON_WORKING_STATUSES:
        return record

    if record.clock_in and record.clock_out:
        gross = _minutes_between(record.clock_in, record.clock_out)
        record.worked_minutes = max(gross - record.break_minutes, 0)

    standard = (
        record.shift.scheduled_minutes if record.shift else DEFAULT_DAY_MINUTES
    )
    if record.worked_minutes > standard:
        record.overtime_minutes = record.worked_minutes - standard

    expected_in = _expected_clock_in(record)
    if expected_in is not None and record.clock_in is not None:
        grace = record.shift.grace_in_minutes
        late = _minutes_between(expected_in, record.clock_in)
        # _minutes_between never returns negative; treat a >12h gap as early.
        if 0 < late <= 12 * 60 and late > grace:
            record.is_late = True
            record.late_minutes = late

    expected_out = _expected_clock_out(record)
    if expected_out is not None and record.clock_out is not None:
        grace = record.shift.grace_out_minutes
        early = _minutes_between(record.clock_out, expected_out)
        if 0 < early <= 12 * 60 and early > grace:
            record.is_early_departure = True
            record.early_departure_minutes = early

    return record


# --- clocking --------------------------------------------------------------

def clock_in(*, tenant, employee, shift=None, when=None) -> AttendanceRecord:
    """Record the employee clocking in. One record per employee per day."""
    when = when or timezone.now()
    work_date = timezone.localdate(when)
    record, _ = AttendanceRecord.objects.get_or_create(
        tenant=tenant,
        employee=employee,
        work_date=work_date,
        defaults={
            "entry_type": EntryType.CLOCK,
            "status": AttendanceStatus.PRESENT,
            "approval_status": ApprovalStatus.APPROVED,
        },
    )
    if record.clock_in is not None:
        raise ValidationError("You have already clocked in today.")
    record.clock_in = when
    record.entry_type = EntryType.CLOCK
    record.status = AttendanceStatus.PRESENT
    record.approval_status = ApprovalStatus.APPROVED
    if shift is not None:
        record.shift = shift
        record.break_minutes = shift.break_minutes
    recalculate_record(record)
    record.save()
    return record


def clock_out(record: AttendanceRecord, *, when=None) -> AttendanceRecord:
    """Record the employee clocking out, finalising the day's figures."""
    if record.clock_in is None:
        raise ValidationError("You cannot clock out before clocking in.")
    if record.clock_out is not None:
        raise ValidationError("You have already clocked out today.")
    record.clock_out = when or timezone.now()
    recalculate_record(record)
    record.save()
    return record


# --- manual entries --------------------------------------------------------

def record_manual_entry(
    *,
    tenant,
    employee,
    work_date,
    shift=None,
    clock_in=None,
    clock_out=None,
    break_minutes=0,
    status=AttendanceStatus.PRESENT,
    notes="",
    auto_approve=False,
) -> AttendanceRecord:
    """Create a manual attendance record (forgotten clock-in, leave day …).

    Manual entries default to pending approval; ``auto_approve`` lets an
    attendance manager record an already-confirmed day.
    """
    if AttendanceRecord.all_objects.filter(
        tenant=tenant, employee=employee, work_date=work_date, is_deleted=False
    ).exists():
        raise ValidationError(
            "An attendance record already exists for this employee on "
            "that date."
        )
    record = AttendanceRecord(
        tenant=tenant,
        employee=employee,
        work_date=work_date,
        shift=shift,
        entry_type=EntryType.MANUAL,
        status=status,
        clock_in=clock_in,
        clock_out=clock_out,
        break_minutes=break_minutes or (shift.break_minutes if shift else 0),
        notes=notes,
        approval_status=(
            ApprovalStatus.APPROVED if auto_approve else ApprovalStatus.PENDING
        ),
    )
    recalculate_record(record)
    record.save()
    return record


def decide_record(
    record: AttendanceRecord, *, approved: bool, user=None, note=""
) -> AttendanceRecord:
    """Approve or reject a pending manual attendance record."""
    if record.approval_status != ApprovalStatus.PENDING:
        raise ValidationError("Only a pending record can be reviewed.")
    record.approval_status = (
        ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
    )
    record.decided_by = user
    record.decided_at = timezone.now()
    if note:
        record.notes = (f"{record.notes}\n{note}".strip() if record.notes
                        else note)
    record.save(update_fields=[
        "approval_status", "decided_by", "decided_at", "notes", "updated_at",
    ])
    return record


# --- timesheets ------------------------------------------------------------

def get_or_create_timesheet(
    *, tenant, employee, period_start, period_end
) -> Timesheet:
    """Fetch (or open) the employee's timesheet for a period."""
    if period_end < period_start:
        raise ValidationError("Period end cannot be before period start.")
    timesheet, _ = Timesheet.objects.get_or_create(
        tenant=tenant,
        employee=employee,
        period_start=period_start,
        period_end=period_end,
        defaults={"status": TimesheetStatus.DRAFT},
    )
    return timesheet


def attach_records(timesheet: Timesheet) -> int:
    """Link every attendance record in the timesheet's period to it."""
    return AttendanceRecord.objects.filter(
        tenant=timesheet.tenant,
        employee=timesheet.employee,
        work_date__gte=timesheet.period_start,
        work_date__lte=timesheet.period_end,
    ).update(timesheet=timesheet)


def submit_timesheet(timesheet: Timesheet) -> Timesheet:
    """Submit a draft (or rejected) timesheet for manager approval."""
    if timesheet.status not in {TimesheetStatus.DRAFT, TimesheetStatus.REJECTED}:
        raise ValidationError(
            "Only a draft or rejected timesheet can be submitted."
        )
    attach_records(timesheet)
    timesheet.status = TimesheetStatus.SUBMITTED
    timesheet.submitted_at = timezone.now()
    timesheet.decided_by = None
    timesheet.decided_at = None
    timesheet.save(update_fields=[
        "status", "submitted_at", "decided_by", "decided_at", "updated_at",
    ])
    return timesheet


def decide_timesheet(
    timesheet: Timesheet, *, approved: bool, user=None, note=""
) -> Timesheet:
    """Approve or reject a submitted timesheet."""
    if timesheet.status != TimesheetStatus.SUBMITTED:
        raise ValidationError("Only a submitted timesheet can be reviewed.")
    timesheet.status = (
        TimesheetStatus.APPROVED if approved else TimesheetStatus.REJECTED
    )
    timesheet.decided_by = user
    timesheet.decided_at = timezone.now()
    timesheet.decision_note = note
    timesheet.save(update_fields=[
        "status", "decided_by", "decided_at", "decision_note", "updated_at",
    ])
    return timesheet


def mark_exported(timesheet: Timesheet) -> Timesheet:
    """Flag an approved timesheet as exported to payroll."""
    if timesheet.status != TimesheetStatus.APPROVED:
        raise ValidationError(
            "Only an approved timesheet can be exported to payroll."
        )
    timesheet.status = TimesheetStatus.EXPORTED
    timesheet.exported_at = timezone.now()
    timesheet.save(update_fields=["status", "exported_at", "updated_at"])
    return timesheet


def timesheet_totals(timesheet: Timesheet) -> dict:
    """Aggregate the figures of a timesheet's linked records."""
    agg = timesheet.records.aggregate(
        days=Count("id"),
        worked_minutes=Sum("worked_minutes"),
        overtime_minutes=Sum("overtime_minutes"),
        late_days=Count("id", filter=Q(is_late=True)),
        absent_days=Count(
            "id", filter=Q(status=AttendanceStatus.ABSENT)
        ),
    )
    return {
        "days": agg["days"] or 0,
        "worked_minutes": agg["worked_minutes"] or 0,
        "overtime_minutes": agg["overtime_minutes"] or 0,
        "late_days": agg["late_days"] or 0,
        "absent_days": agg["absent_days"] or 0,
    }


def export_rows(timesheet: Timesheet):
    """Columns + rows for a payroll-facing CSV/XLSX export of a timesheet."""
    columns = [
        {"key": "work_date", "label": "Date"},
        {"key": "status", "label": "Status"},
        {"key": "worked_hours", "label": "Worked hours"},
        {"key": "overtime_hours", "label": "Overtime hours"},
        {"key": "late_minutes", "label": "Late (min)"},
        {"key": "approval_status", "label": "Approval"},
    ]
    rows = []
    for record in timesheet.records.order_by("work_date"):
        rows.append({
            "work_date": record.work_date.isoformat(),
            "status": record.get_status_display(),
            "worked_hours": round(record.worked_minutes / 60, 2),
            "overtime_hours": round(record.overtime_minutes / 60, 2),
            "late_minutes": record.late_minutes,
            "approval_status": record.get_approval_status_display(),
        })
    return columns, rows


# --- exceptions ------------------------------------------------------------

def attendance_exceptions(queryset):
    """Filter an attendance queryset down to records needing attention."""
    return queryset.filter(
        Q(is_late=True)
        | Q(is_early_departure=True)
        | Q(status=AttendanceStatus.ABSENT)
        | Q(approval_status=ApprovalStatus.PENDING)
    )
