"""Payroll business logic (spec §9.10).

Covers record generation (salary snapshot + leave-without-pay), the
gross / net calculation, period status transitions and payslip
generation. Viewsets delegate every figure-producing step here so the
arithmetic lives in one place.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from rest_framework.exceptions import ValidationError

from apps.employees.enums import EXITED_STATUSES
from apps.employees.models import Employee
from apps.leave.enums import LeaveRequestStatus
from apps.leave.models import LeaveRequest
from apps.leave.services import working_days
from apps.notifications import services as notifications
from apps.notifications.enums import NotificationType

from .enums import ComponentType, LOCKED_PERIOD_STATUSES, PayrollStatus, RecordStatus
from .models import PayrollPeriod, PayrollRecord, Payslip

ZERO = Decimal("0.00")


def _money(value) -> Decimal:
    """Quantise a value to 2dp using bankers-safe half-up rounding."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------
# Leave-without-pay
# --------------------------------------------------------------------------
def leave_without_pay_days(employee, period: PayrollPeriod) -> Decimal:
    """Unpaid-leave days for an employee within a period.

    Unpaid leave is approved leave on a leave type flagged ``is_paid =
    False`` whose start date falls within the period.
    """
    requests = LeaveRequest.objects.filter(
        tenant=period.tenant,
        employee=employee,
        status=LeaveRequestStatus.APPROVED,
        leave_type__is_paid=False,
        start_date__gte=period.start_date,
        start_date__lte=period.end_date,
    )
    return Decimal(sum((r.total_days for r in requests), ZERO))


def _lwp_amount(basic_salary: Decimal, days: Decimal, period: PayrollPeriod) -> Decimal:
    """Pro-rata salary deduction for ``days`` of unpaid leave."""
    if days <= 0 or basic_salary <= 0:
        return ZERO
    period_working_days = working_days(period.start_date, period.end_date)
    if period_working_days <= 0:
        return ZERO
    daily_rate = basic_salary / period_working_days
    return _money(daily_rate * days)


# --------------------------------------------------------------------------
# Calculation
# --------------------------------------------------------------------------
def recalculate_record(record: PayrollRecord) -> PayrollRecord:
    """Recompute a record's totals, leave-without-pay and gross / net pay."""
    lines = list(record.lines.all())
    allowances = sum(
        (l.amount for l in lines if l.line_type == ComponentType.ALLOWANCE), ZERO
    )
    deductions = sum(
        (l.amount for l in lines if l.line_type == ComponentType.DEDUCTION), ZERO
    )

    days = leave_without_pay_days(record.employee, record.period)
    lwp_amount = _lwp_amount(record.basic_salary, days, record.period)

    gross = _money(record.basic_salary + allowances + record.overtime_amount)
    net = _money(gross - deductions - lwp_amount)

    record.total_allowances = _money(allowances)
    record.total_deductions = _money(deductions)
    record.leave_without_pay_days = days
    record.leave_without_pay_amount = lwp_amount
    record.gross_pay = gross
    record.net_pay = net
    record.save(update_fields=[
        "total_allowances", "total_deductions", "leave_without_pay_days",
        "leave_without_pay_amount", "gross_pay", "net_pay", "updated_at",
    ])
    return record


# --------------------------------------------------------------------------
# Record generation
# --------------------------------------------------------------------------
def generate_records(period: PayrollPeriod) -> int:
    """Create a draft payroll record for every active employee.

    Idempotent: employees that already have a record for the period are
    left untouched. Returns the number of records created.
    """
    if period.status in LOCKED_PERIOD_STATUSES:
        raise ValidationError(
            "Records cannot be generated for an approved or paid period."
        )
    employees = Employee.objects.filter(tenant=period.tenant).exclude(
        employment_status__in=EXITED_STATUSES
    )
    created = 0
    for employee in employees:
        record, was_created = PayrollRecord.objects.get_or_create(
            tenant=period.tenant,
            period=period,
            employee=employee,
            defaults={
                "basic_salary": employee.current_salary or ZERO,
                "currency": employee.salary_currency or "GBP",
            },
        )
        if was_created:
            recalculate_record(record)
            created += 1
    if period.status == PayrollStatus.DRAFT and created:
        period.status = PayrollStatus.PROCESSING
        period.save(update_fields=["status", "updated_at"])
    return created


# --------------------------------------------------------------------------
# Period transitions
# --------------------------------------------------------------------------
def approve_period(period: PayrollPeriod, *, user) -> PayrollPeriod:
    """Approve a period — locks records and marks them approved."""
    if period.status not in {PayrollStatus.DRAFT, PayrollStatus.PROCESSING}:
        raise ValidationError("Only a draft or processing period can be approved.")
    if not period.records.exists():
        raise ValidationError("Generate payroll records before approving.")
    period.status = PayrollStatus.APPROVED
    period.approved_by = user
    period.approved_at = timezone.now()
    period.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    period.records.update(status=RecordStatus.APPROVED, updated_at=timezone.now())
    return period


def mark_period_paid(period: PayrollPeriod) -> PayrollPeriod:
    """Mark an approved period (and its records) as paid."""
    if period.status != PayrollStatus.APPROVED:
        raise ValidationError("Only an approved period can be marked paid.")
    period.status = PayrollStatus.PAID
    period.save(update_fields=["status", "updated_at"])
    period.records.update(status=RecordStatus.PAID, updated_at=timezone.now())
    return period


# --------------------------------------------------------------------------
# Payslips
# --------------------------------------------------------------------------
def _payslip_reference(record: PayrollRecord) -> str:
    return f"PS-{record.period.code}-{record.employee.employee_number}"


def _build_snapshot(record: PayrollRecord) -> dict:
    """Freeze a record's breakdown for the payslip."""
    return {
        "employee": record.employee.full_name,
        "employee_number": record.employee.employee_number,
        "period": record.period.name,
        "currency": record.currency,
        "basic_salary": str(record.basic_salary),
        "allowances": [
            {"description": l.description, "amount": str(l.amount)}
            for l in record.lines.all() if l.line_type == ComponentType.ALLOWANCE
        ],
        "deductions": [
            {"description": l.description, "amount": str(l.amount)}
            for l in record.lines.all() if l.line_type == ComponentType.DEDUCTION
        ],
        "overtime_amount": str(record.overtime_amount),
        "leave_without_pay_days": str(record.leave_without_pay_days),
        "leave_without_pay_amount": str(record.leave_without_pay_amount),
        "gross_pay": str(record.gross_pay),
        "net_pay": str(record.net_pay),
    }


def generate_payslip(record: PayrollRecord) -> Payslip:
    """Create or refresh the payslip for a record (unpublished)."""
    payslip, _ = Payslip.objects.update_or_create(
        tenant=record.tenant,
        record=record,
        defaults={
            "employee": record.employee,
            "period": record.period,
            "reference": _payslip_reference(record),
            "snapshot": _build_snapshot(record),
        },
    )
    return payslip


def publish_payslip(payslip: Payslip) -> Payslip:
    """Publish a payslip and notify the employee."""
    payslip.is_published = True
    payslip.published_at = timezone.now()
    payslip.save(update_fields=["is_published", "published_at", "updated_at"])

    user = getattr(payslip.employee, "user", None)
    notifications.dispatch(
        tenant=payslip.tenant,
        event_key=NotificationType.PAYSLIP_PUBLISHED,
        users=[user] if user else [],
        context={
            "period": payslip.period.name,
            "net_pay": f"{payslip.record.currency} {payslip.record.net_pay}",
        },
        entity_type="payroll.payslip",
        entity_id=str(payslip.pk),
    )
    return payslip


def export_rows(period: PayrollPeriod) -> tuple[list[dict], list[dict]]:
    """Return (columns, rows) for a period's payroll export."""
    columns = [
        {"key": "employee", "label": "Employee"},
        {"key": "employee_number", "label": "Employee #"},
        {"key": "basic_salary", "label": "Basic salary"},
        {"key": "total_allowances", "label": "Allowances"},
        {"key": "overtime_amount", "label": "Overtime"},
        {"key": "total_deductions", "label": "Deductions"},
        {"key": "leave_without_pay_amount", "label": "Leave w/o pay"},
        {"key": "gross_pay", "label": "Gross pay"},
        {"key": "net_pay", "label": "Net pay"},
        {"key": "currency", "label": "Currency"},
        {"key": "status", "label": "Status"},
    ]
    rows = [
        {
            "employee": r.employee.full_name,
            "employee_number": r.employee.employee_number,
            "basic_salary": r.basic_salary,
            "total_allowances": r.total_allowances,
            "overtime_amount": r.overtime_amount,
            "total_deductions": r.total_deductions,
            "leave_without_pay_amount": r.leave_without_pay_amount,
            "gross_pay": r.gross_pay,
            "net_pay": r.net_pay,
            "currency": r.currency,
            "status": r.get_status_display(),
        }
        for r in period.records.select_related("employee")
    ]
    return columns, rows
