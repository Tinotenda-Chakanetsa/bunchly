"""Learning & development business logic (spec §9.19).

Covers course assignment, the training-record lifecycle (including
certification dating), certification expiry and compliance status.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .enums import (
    OPEN_RECORD_STATUSES,
    RecordStatus,
    VALID_COMPLETION_STATUSES,
)
from .models import TrainingCourse, TrainingRecord


def _add_months(start: date, months: int) -> date:
    """Add a whole number of months to a date, clamping the day-of-month."""
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


# --------------------------------------------------------------------------
# Assignment
# --------------------------------------------------------------------------
def assign_course(
    *,
    tenant,
    employee,
    course: TrainingCourse,
    assigned_by=None,
    due_date=None,
) -> TrainingRecord:
    """Assign a course to an employee, creating a training record.

    Refuses a duplicate while an open record for the same course exists.
    """
    open_record = TrainingRecord.objects.filter(
        tenant=tenant,
        employee=employee,
        course=course,
        status__in=OPEN_RECORD_STATUSES,
    ).exists()
    if open_record:
        raise ValidationError(
            f"{employee} already has an open record for '{course.name}'."
        )
    return TrainingRecord.objects.create(
        tenant=tenant,
        employee=employee,
        course=course,
        status=RecordStatus.ASSIGNED,
        assigned_by=assigned_by,
        assigned_date=timezone.now().date(),
        due_date=due_date,
    )


# --------------------------------------------------------------------------
# Record lifecycle
# --------------------------------------------------------------------------
def start_record(record: TrainingRecord) -> TrainingRecord:
    """Mark an assigned record as in progress."""
    if record.status != RecordStatus.ASSIGNED:
        raise ValidationError("Only an assigned record can be started.")
    record.status = RecordStatus.IN_PROGRESS
    record.started_at = timezone.now().date()
    record.save(update_fields=["status", "started_at", "updated_at"])
    return record


def complete_record(
    record: TrainingRecord,
    *,
    score: int | None = None,
    certificate_number: str = "",
    completed_date=None,
) -> TrainingRecord:
    """Complete a training record, applying pass score and certification.

    A pass/fail is derived from the course ``pass_score``; on a pass with
    a certifying course the certificate expiry is dated from the course's
    validity window.
    """
    if record.status not in {RecordStatus.ASSIGNED, RecordStatus.IN_PROGRESS}:
        raise ValidationError("Only an open record can be completed.")

    course = record.course
    completed_date = completed_date or timezone.now().date()
    passed = True
    if course.pass_score and score is not None:
        passed = score >= course.pass_score

    record.score = score
    record.passed = passed
    record.completed_date = completed_date
    record.status = RecordStatus.COMPLETED if passed else RecordStatus.FAILED

    if passed and course.provides_certification:
        record.certificate_number = certificate_number
        if course.certification_validity_months:
            record.certificate_expiry_date = _add_months(
                completed_date, course.certification_validity_months
            )
    record.save(update_fields=[
        "score", "passed", "completed_date", "status",
        "certificate_number", "certificate_expiry_date", "updated_at",
    ])
    return record


def cancel_record(record: TrainingRecord) -> TrainingRecord:
    """Cancel an open training record."""
    if record.status not in OPEN_RECORD_STATUSES:
        raise ValidationError("Only an open record can be cancelled.")
    record.status = RecordStatus.CANCELLED
    record.save(update_fields=["status", "updated_at"])
    return record


# --------------------------------------------------------------------------
# Certification expiry & compliance
# --------------------------------------------------------------------------
def expire_certifications(tenant=None, *, on_date=None) -> int:
    """Flip completed records whose certification has lapsed to ``expired``.

    Returns the number transitioned. Safe to run repeatedly.
    """
    on_date = on_date or timezone.now().date()
    queryset = TrainingRecord.objects.filter(
        status=RecordStatus.COMPLETED,
        certificate_expiry_date__isnull=False,
        certificate_expiry_date__lt=on_date,
    )
    if tenant is not None:
        queryset = queryset.filter(tenant=tenant)
    return queryset.update(status=RecordStatus.EXPIRED, updated_at=timezone.now())


def expiring_certifications(tenant, *, within_days: int = 30):
    """Completed records whose certification expires within ``within_days``."""
    today = timezone.now().date()
    horizon = today + timedelta(days=within_days)
    return TrainingRecord.objects.filter(
        tenant=tenant,
        status=RecordStatus.COMPLETED,
        certificate_expiry_date__isnull=False,
        certificate_expiry_date__gte=today,
        certificate_expiry_date__lte=horizon,
    ).select_related("employee", "course")


def compliance_status(employee) -> dict:
    """An employee's standing against the tenant's compliance courses."""
    courses = TrainingCourse.objects.filter(
        tenant=employee.tenant, is_compliance=True, is_active=True
    )
    completed_ids = set(
        TrainingRecord.objects.filter(
            tenant=employee.tenant,
            employee=employee,
            status__in=VALID_COMPLETION_STATUSES,
        ).values_list("course_id", flat=True)
    )
    outstanding = [c for c in courses if c.id not in completed_ids]
    return {
        "employee": str(employee.pk),
        "compliance_courses": courses.count(),
        "completed": len(completed_ids & {c.id for c in courses}),
        "outstanding": [
            {"id": str(c.id), "name": c.name, "code": c.code} for c in outstanding
        ],
        "is_compliant": not outstanding,
    }
