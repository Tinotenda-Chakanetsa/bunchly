"""Date-triggered HR alerts (spec §9.15 — scheduled daily job).

``run_scheduled_alerts`` is the entry point the Celery beat task calls
once a day. It scans every tenant for birthdays, contract / probation /
retirement milestones, expiring documents and stale leave approvals, and
raises the matching notification through ``services.dispatch``.

Trigger windows default to the spec's values but can be overridden per
tenant via ``TenantSettings.module_flags`` (e.g. ``contract_expiry_days``).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

from apps.employees.enums import EXITED_STATUSES
from apps.employees.models import Employee
from apps.tenants.models import Tenant

from . import services
from .enums import NotificationType

logger = logging.getLogger("bunchly.notifications")

# Default trigger windows (days before the event).
DEFAULT_CONTRACT_EXPIRY_DAYS = [90, 60, 30]
DEFAULT_PROBATION_END_DAYS = [14, 7]
DEFAULT_RETIREMENT_DAYS = [180, 90]
DEFAULT_DOCUMENT_EXPIRY_DAYS = [30, 14, 7]
LEAVE_REMINDER_AGE_DAYS = 3


def _flag(tenant, key: str, default: list[int]) -> list[int]:
    """Per-tenant override of a trigger window, falling back to the default."""
    flags = getattr(getattr(tenant, "settings", None), "module_flags", None) or {}
    value = flags.get(key)
    if isinstance(value, list) and all(isinstance(v, int) for v in value):
        return value
    return default


def _configured_emails(tenant, event_key: str) -> list[str]:
    """Tenant-configured extra recipients for an event (never hard-coded)."""
    tenant_settings = getattr(tenant, "settings", None)
    if tenant_settings is None:
        return []
    return list((tenant_settings.notification_recipients or {}).get(event_key, []))


def _active_employees(tenant):
    return Employee.objects.filter(tenant=tenant).exclude(
        employment_status__in=EXITED_STATUSES
    ).select_related("user", "line_manager", "line_manager__user")


def _user_of(employee) -> object | None:
    return getattr(employee, "user", None)


# --------------------------------------------------------------------------
# Individual alert scans
# --------------------------------------------------------------------------
def _birthday_alerts(tenant, today) -> int:
    sent = 0
    extra = _configured_emails(tenant, NotificationType.BIRTHDAY)
    for emp in _active_employees(tenant):
        dob = emp.date_of_birth
        if dob and dob.month == today.month and dob.day == today.day:
            services.dispatch(
                tenant=tenant,
                event_key=NotificationType.BIRTHDAY,
                users=[_user_of(emp), _user_of(emp.line_manager) if emp.line_manager else None],
                extra_emails=extra,
                context={"employee_name": emp.full_name},
                entity_type="employees.employee",
                entity_id=str(emp.pk),
            )
            sent += 1
    return sent


def _milestone_alerts(
    tenant, today, *, field: str, windows: list[int], event_key: str,
    context_date_key: str, include_employee: bool,
) -> int:
    """Generic 'date field is N days away' scan shared by several alerts."""
    sent = 0
    extra = _configured_emails(tenant, event_key)
    target_dates = {today + timedelta(days=n): n for n in windows}
    lookup = {f"{field}__in": list(target_dates)}
    for emp in _active_employees(tenant).filter(**lookup):
        value = getattr(emp, field)
        users = []
        if include_employee:
            users.append(_user_of(emp))
        if emp.line_manager:
            users.append(_user_of(emp.line_manager))
        services.dispatch(
            tenant=tenant,
            event_key=event_key,
            users=users,
            extra_emails=extra,
            context={
                "employee_name": emp.full_name,
                context_date_key: str(value),
                "expiry_date": str(value),
                "days_remaining": target_dates.get(value, ""),
            },
            level="warning",
            entity_type="employees.employee",
            entity_id=str(emp.pk),
        )
        sent += 1
    return sent


def _document_expiry_alerts(tenant, today) -> int:
    from apps.documents.enums import DocumentStatus
    from apps.documents.models import Document

    sent = 0
    extra = _configured_emails(tenant, NotificationType.DOCUMENT_EXPIRING)
    windows = _flag(tenant, "document_expiry_days", DEFAULT_DOCUMENT_EXPIRY_DAYS)
    target_dates = [today + timedelta(days=n) for n in windows]
    documents = Document.objects.filter(
        tenant=tenant,
        status=DocumentStatus.APPROVED,
        expiry_date__in=target_dates,
    ).select_related("employee", "employee__user", "category")
    for doc in documents:
        services.dispatch(
            tenant=tenant,
            event_key=NotificationType.DOCUMENT_EXPIRING,
            users=[_user_of(doc.employee)],
            extra_emails=extra,
            context={
                "document_title": doc.title,
                "employee_name": doc.employee.full_name,
                "expiry_date": str(doc.expiry_date),
            },
            level="warning",
            entity_type="documents.document",
            entity_id=str(doc.pk),
        )
        sent += 1
    return sent


def _leave_pending_reminders(tenant, today) -> int:
    from apps.leave.enums import ApprovalStage, LeaveRequestStatus
    from apps.leave.models import LeaveRequest

    sent = 0
    extra = _configured_emails(tenant, NotificationType.LEAVE_PENDING_REMINDER)
    cutoff = timezone.now() - timedelta(days=LEAVE_REMINDER_AGE_DAYS)
    stale = LeaveRequest.objects.filter(
        tenant=tenant,
        status=LeaveRequestStatus.PENDING,
        submitted_at__lt=cutoff,
    ).select_related(
        "employee", "employee__line_manager", "employee__line_manager__user",
        "leave_type",
    )
    for req in stale:
        users = []
        if req.current_stage == ApprovalStage.MANAGER and req.employee.line_manager:
            users.append(_user_of(req.employee.line_manager))
        services.dispatch(
            tenant=tenant,
            event_key=NotificationType.LEAVE_PENDING_REMINDER,
            users=users,
            extra_emails=extra,
            context={
                "employee_name": req.employee.full_name,
                "leave_type": req.leave_type.name,
                "start_date": str(req.start_date),
                "end_date": str(req.end_date),
                "submitted_date": str(
                    req.submitted_at.date() if req.submitted_at else ""
                ),
            },
            level="warning",
            entity_type="leave.leave_request",
            entity_id=str(req.pk),
        )
        sent += 1
    return sent


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def run_scheduled_alerts(today=None) -> dict[str, int]:
    """Scan every tenant and raise all date-triggered notifications.

    Returns a per-category count summary. Idempotent within a day only in
    the sense that running twice sends twice — schedule it once daily.
    """
    today = today or timezone.now().date()
    totals = {
        "birthday": 0, "contract_expiry": 0, "probation_ending": 0,
        "retirement": 0, "document_expiring": 0, "leave_pending": 0,
    }
    for tenant in Tenant.objects.all():
        try:
            totals["birthday"] += _birthday_alerts(tenant, today)
            totals["contract_expiry"] += _milestone_alerts(
                tenant, today, field="contract_end_date",
                windows=_flag(tenant, "contract_expiry_days", DEFAULT_CONTRACT_EXPIRY_DAYS),
                event_key=NotificationType.CONTRACT_EXPIRY,
                context_date_key="expiry_date", include_employee=True,
            )
            totals["probation_ending"] += _milestone_alerts(
                tenant, today, field="probation_end_date",
                windows=_flag(tenant, "probation_end_days", DEFAULT_PROBATION_END_DAYS),
                event_key=NotificationType.PROBATION_ENDING,
                context_date_key="probation_end_date", include_employee=False,
            )
            totals["retirement"] += _milestone_alerts(
                tenant, today, field="retirement_date",
                windows=_flag(tenant, "retirement_days", DEFAULT_RETIREMENT_DAYS),
                event_key=NotificationType.RETIREMENT_REMINDER,
                context_date_key="retirement_date", include_employee=True,
            )
            totals["document_expiring"] += _document_expiry_alerts(tenant, today)
            totals["leave_pending"] += _leave_pending_reminders(tenant, today)
        except Exception:  # pragma: no cover - one tenant must not break the rest
            logger.exception("scheduled alerts failed for tenant %s", tenant.pk)
    logger.info("scheduled alerts complete: %s", totals)
    return totals
