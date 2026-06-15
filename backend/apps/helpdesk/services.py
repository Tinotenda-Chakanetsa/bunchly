"""HR helpdesk business logic (spec §9.22).

Covers case creation (with SLA dating from the category), the status
lifecycle and SLA overdue detection.
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .enums import CLOSED_CASE_STATUSES, OPEN_CASE_STATUSES, CaseStatus
from .models import CaseCategory, HRCase


def generate_reference(tenant) -> str:
    """A per-tenant sequential case reference (CASE-00001)."""
    count = HRCase.all_objects.filter(tenant=tenant).count()
    return f"CASE-{count + 1:05d}"


def create_case(
    *,
    tenant,
    raised_by,
    subject: str,
    description: str = "",
    category: CaseCategory | None = None,
    priority: str | None = None,
    source_inbound_email=None,
) -> HRCase:
    """Open an HR case, dating its SLA target from the category."""
    sla_due_at = None
    if category is not None and category.default_sla_hours:
        sla_due_at = timezone.now() + timedelta(hours=category.default_sla_hours)

    case = HRCase(
        tenant=tenant,
        reference=generate_reference(tenant),
        subject=subject,
        description=description,
        category=category,
        raised_by=raised_by,
        status=CaseStatus.OPEN,
        sla_due_at=sla_due_at,
        source_inbound_email=source_inbound_email,
    )
    if priority:
        case.priority = priority
    case.save()
    return case


def assign_case(case: HRCase, *, user) -> HRCase:
    """Assign a case to an HR handler; an open case starts progressing."""
    if case.status in CLOSED_CASE_STATUSES:
        raise ValidationError("A closed case cannot be reassigned.")
    case.assigned_to = user
    if case.status == CaseStatus.OPEN:
        case.status = CaseStatus.IN_PROGRESS
    case.save(update_fields=["assigned_to", "status", "updated_at"])
    return case


def change_status(case: HRCase, status: str) -> HRCase:
    """Move a case between the open-work statuses (open / in progress / hold)."""
    if status not in OPEN_CASE_STATUSES:
        raise ValidationError(
            {"status": "Use resolve / close / reopen for terminal transitions."}
        )
    if case.status in CLOSED_CASE_STATUSES:
        raise ValidationError("Reopen the case before changing its status.")
    case.status = status
    case.save(update_fields=["status", "updated_at"])
    return case


def resolve_case(case: HRCase, *, resolution_notes: str = "") -> HRCase:
    """Resolve an open case, recording the resolution notes."""
    if case.status not in OPEN_CASE_STATUSES:
        raise ValidationError("Only an open case can be resolved.")
    case.status = CaseStatus.RESOLVED
    case.resolved_at = timezone.now()
    case.resolution_notes = resolution_notes
    case.save(update_fields=[
        "status", "resolved_at", "resolution_notes", "updated_at",
    ])
    return case


def close_case(case: HRCase) -> HRCase:
    """Close a resolved case."""
    if case.status != CaseStatus.RESOLVED:
        raise ValidationError("Only a resolved case can be closed.")
    case.status = CaseStatus.CLOSED
    case.closed_at = timezone.now()
    case.save(update_fields=["status", "closed_at", "updated_at"])
    return case


def cancel_case(case: HRCase) -> HRCase:
    """Cancel a case that is not already closed."""
    if case.status in CLOSED_CASE_STATUSES:
        raise ValidationError("This case is already closed.")
    case.status = CaseStatus.CANCELLED
    case.closed_at = timezone.now()
    case.save(update_fields=["status", "closed_at", "updated_at"])
    return case


def reopen_case(case: HRCase) -> HRCase:
    """Reopen a resolved / closed case."""
    if case.status not in {CaseStatus.RESOLVED, CaseStatus.CLOSED}:
        raise ValidationError("Only a resolved or closed case can be reopened.")
    case.status = CaseStatus.IN_PROGRESS
    case.resolved_at = None
    case.closed_at = None
    case.save(update_fields=["status", "resolved_at", "closed_at", "updated_at"])
    return case


def overdue_cases(tenant):
    """Open cases whose SLA target has passed."""
    return HRCase.objects.filter(
        tenant=tenant,
        status__in=OPEN_CASE_STATUSES,
        sla_due_at__isnull=False,
        sla_due_at__lt=timezone.now(),
    ).select_related("category", "raised_by", "assigned_to")
