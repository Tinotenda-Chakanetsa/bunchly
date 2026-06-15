"""Benefits-administration business logic (spec §9.11).

Holds the eligibility checks, the enrolment lifecycle (enrol -> approve /
decline -> suspend / resume / terminate) and contribution resolution.
Every state change records a ``BenefitEnrolmentHistory`` row.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .enums import ContributionBasis, EnrolmentEvent, EnrolmentStatus
from .models import BenefitEnrolmentHistory, BenefitType, EmployeeBenefit

ZERO = Decimal("0.00")


def _money(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------
# Eligibility & contributions
# --------------------------------------------------------------------------
def months_of_service(employee, *, on: date | None = None) -> int:
    """Whole months between an employee's start date and ``on`` (today)."""
    on = on or timezone.now().date()
    start = employee.start_date
    if start is None or start > on:
        return 0
    return (on.year - start.year) * 12 + (on.month - start.month) - (
        1 if on.day < start.day else 0
    )


def check_eligibility(employee, benefit_type: BenefitType) -> None:
    """Raise if the employee may not enrol in the benefit type."""
    if not benefit_type.is_active:
        raise ValidationError("This benefit is not currently offered.")
    if benefit_type.eligible_employment_statuses:
        if employee.employment_status not in benefit_type.eligible_employment_statuses:
            raise ValidationError(
                "Your employment status is not eligible for this benefit."
            )
    if benefit_type.eligibility_min_months:
        served = months_of_service(employee)
        if served < benefit_type.eligibility_min_months:
            raise ValidationError(
                f"This benefit requires {benefit_type.eligibility_min_months} "
                f"months of service ({served} completed)."
            )


def resolve_contributions(benefit_type: BenefitType, employee) -> tuple[Decimal, Decimal]:
    """Resolve (employee, employer) contribution amounts for an enrolment.

    For a percentage-basis benefit the stored figures are percentages of
    the employee's basic salary; for a fixed basis they are used as-is.
    """
    if benefit_type.contribution_basis == ContributionBasis.PERCENTAGE:
        salary = employee.current_salary or ZERO
        return (
            _money(salary * benefit_type.employee_contribution / 100),
            _money(salary * benefit_type.employer_contribution / 100),
        )
    return (
        _money(benefit_type.employee_contribution),
        _money(benefit_type.employer_contribution),
    )


# --------------------------------------------------------------------------
# Enrolment lifecycle
# --------------------------------------------------------------------------
def _log(enrolment, event, *, user=None, note=""):
    BenefitEnrolmentHistory.objects.create(
        tenant=enrolment.tenant,
        enrolment=enrolment,
        event=event,
        note=note[:255],
        actor=user,
    )


def enrol(employee, benefit_type: BenefitType, *, user=None, notes: str = "") -> EmployeeBenefit:
    """Create an enrolment for an employee in a benefit type."""
    check_eligibility(employee, benefit_type)

    open_enrolment = EmployeeBenefit.objects.filter(
        tenant=benefit_type.tenant,
        employee=employee,
        benefit_type=benefit_type,
        status__in=[
            EnrolmentStatus.PENDING,
            EnrolmentStatus.ACTIVE,
            EnrolmentStatus.SUSPENDED,
        ],
    ).exists()
    if open_enrolment:
        raise ValidationError(
            "The employee already has an open enrolment in this benefit."
        )

    employee_amount, employer_amount = resolve_contributions(benefit_type, employee)
    auto_active = not benefit_type.requires_approval
    enrolment = EmployeeBenefit.objects.create(
        tenant=benefit_type.tenant,
        employee=employee,
        benefit_type=benefit_type,
        status=EnrolmentStatus.ACTIVE if auto_active else EnrolmentStatus.PENDING,
        start_date=timezone.now().date() if auto_active else None,
        employee_contribution=employee_amount,
        employer_contribution=employer_amount,
        notes=notes,
    )
    _log(enrolment, EnrolmentEvent.ENROLLED, user=user)
    if auto_active:
        _log(enrolment, EnrolmentEvent.APPROVED, user=user,
             note="Auto-approved — no approval required.")
    return enrolment


def approve_enrolment(enrolment: EmployeeBenefit, *, user) -> EmployeeBenefit:
    """Approve a pending enrolment — it becomes active."""
    if enrolment.status != EnrolmentStatus.PENDING:
        raise ValidationError("Only a pending enrolment can be approved.")
    enrolment.status = EnrolmentStatus.ACTIVE
    enrolment.start_date = enrolment.start_date or timezone.now().date()
    enrolment.approved_by = user
    enrolment.approved_at = timezone.now()
    enrolment.save(update_fields=[
        "status", "start_date", "approved_by", "approved_at", "updated_at",
    ])
    _log(enrolment, EnrolmentEvent.APPROVED, user=user)
    return enrolment


def decline_enrolment(enrolment, *, user, note: str = "") -> EmployeeBenefit:
    """Decline a pending enrolment."""
    if enrolment.status != EnrolmentStatus.PENDING:
        raise ValidationError("Only a pending enrolment can be declined.")
    enrolment.status = EnrolmentStatus.DECLINED
    enrolment.save(update_fields=["status", "updated_at"])
    _log(enrolment, EnrolmentEvent.DECLINED, user=user, note=note)
    return enrolment


def suspend_enrolment(enrolment, *, user, note: str = "") -> EmployeeBenefit:
    """Suspend an active enrolment."""
    if enrolment.status != EnrolmentStatus.ACTIVE:
        raise ValidationError("Only an active enrolment can be suspended.")
    enrolment.status = EnrolmentStatus.SUSPENDED
    enrolment.save(update_fields=["status", "updated_at"])
    _log(enrolment, EnrolmentEvent.SUSPENDED, user=user, note=note)
    return enrolment


def resume_enrolment(enrolment, *, user) -> EmployeeBenefit:
    """Resume a suspended enrolment."""
    if enrolment.status != EnrolmentStatus.SUSPENDED:
        raise ValidationError("Only a suspended enrolment can be resumed.")
    enrolment.status = EnrolmentStatus.ACTIVE
    enrolment.save(update_fields=["status", "updated_at"])
    _log(enrolment, EnrolmentEvent.RESUMED, user=user)
    return enrolment


def terminate_enrolment(enrolment, *, user, note: str = "") -> EmployeeBenefit:
    """Terminate an enrolment (active or suspended)."""
    if enrolment.status not in {EnrolmentStatus.ACTIVE, EnrolmentStatus.SUSPENDED}:
        raise ValidationError("Only an active or suspended enrolment can be terminated.")
    enrolment.status = EnrolmentStatus.TERMINATED
    enrolment.end_date = timezone.now().date()
    enrolment.save(update_fields=["status", "end_date", "updated_at"])
    _log(enrolment, EnrolmentEvent.TERMINATED, user=user, note=note)
    return enrolment


# --------------------------------------------------------------------------
# Payroll integration helper
# --------------------------------------------------------------------------
def active_enrolments(employee):
    """An employee's currently in-force benefit enrolments."""
    return EmployeeBenefit.objects.filter(
        tenant=employee.tenant,
        employee=employee,
        status=EnrolmentStatus.ACTIVE,
    ).select_related("benefit_type", "benefit_type__pay_component")


def benefit_deduction_lines(employee) -> list[dict]:
    """Benefit contributions expressible as payroll deduction lines.

    Returned as plain dicts so the payroll module can create
    ``PayrollLine`` rows from them without a hard dependency on benefits.
    """
    lines = []
    for enrolment in active_enrolments(employee):
        if enrolment.employee_contribution <= 0:
            continue
        lines.append({
            "component": enrolment.benefit_type.pay_component_id,
            "description": f"{enrolment.benefit_type.name} (benefit)",
            "amount": enrolment.employee_contribution,
            "is_taxable": enrolment.benefit_type.is_taxable,
        })
    return lines
