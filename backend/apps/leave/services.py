"""Leave business logic — working-day maths, balances, workflow, notices.

The viewsets stay thin: they delegate every state change to the helpers
here so the rules (entitlement, accrual, carry-forward, the approval
chain, conflict detection) live in one auditable place.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .enums import (
    AccrualMethod,
    ACTIVE_STATUSES,
    ApprovalStage,
    ApprovalStatus,
    DayPortion,
    GenderEligibility,
    LeaveRequestStatus,
)
from .models import ZERO, LeaveApproval, LeaveBalance, LeaveRequest, LeaveType

HALF = Decimal("0.5")


# --------------------------------------------------------------------------
# Working-day arithmetic
# --------------------------------------------------------------------------
def working_days(
    start: date,
    end: date,
    start_portion: str = DayPortion.FULL,
    end_portion: str = DayPortion.FULL,
) -> Decimal:
    """Count Mon-Fri days between two dates, honouring half-day portions.

    Public holidays are not subtracted — a tenant holiday calendar is a
    later module; for now weekends are the only non-working days.
    """
    if end < start:
        raise ValidationError({"end_date": "End date cannot be before the start date."})

    weekday_count = sum(
        1
        for n in range((end - start).days + 1)
        if (start + timedelta(days=n)).weekday() < 5
    )
    if weekday_count == 0:
        return ZERO

    if start == end:
        return HALF if start_portion != DayPortion.FULL else Decimal("1")

    total = Decimal(weekday_count)
    if start_portion != DayPortion.FULL and start.weekday() < 5:
        total -= HALF
    if end_portion != DayPortion.FULL and end.weekday() < 5:
        total -= HALF
    return total


# --------------------------------------------------------------------------
# Balances & accrual
# --------------------------------------------------------------------------
def _entitlement_for(leave_type: LeaveType, year: int) -> Decimal:
    """Days to grant a freshly created balance for ``year``."""
    full = leave_type.default_annual_days or ZERO
    if leave_type.accrual_method != AccrualMethod.MONTHLY:
        return full
    # Monthly accrual: prorate to the current month for the live year.
    today = timezone.now().date()
    months = today.month if today.year == year else 12
    return (full * Decimal(months) / Decimal(12)).quantize(Decimal("0.01"))


def get_or_create_balance(employee, leave_type: LeaveType, year: int) -> LeaveBalance:
    """Return the employee's balance for a leave type/year, creating it."""
    balance, created = LeaveBalance.objects.get_or_create(
        tenant=employee.tenant,
        employee=employee,
        leave_type=leave_type,
        year=year,
        defaults={"entitled_days": _entitlement_for(leave_type, year)},
    )
    return balance


def recalculate_balance(balance: LeaveBalance) -> LeaveBalance:
    """Recompute taken/pending from the request rows that draw on a balance.

    Defensive — keeps a balance consistent if a request was edited
    outside the normal workflow.
    """
    taken = ZERO
    pending = ZERO
    for req in balance.requests.all():
        if req.status == LeaveRequestStatus.APPROVED:
            taken += req.total_days
        elif req.status == LeaveRequestStatus.PENDING:
            pending += req.total_days
    balance.taken_days = taken
    balance.pending_days = pending
    balance.save(update_fields=["taken_days", "pending_days", "updated_at"])
    return balance


def roll_over_balances(tenant, from_year: int, to_year: int) -> int:
    """Carry unused balance from one year into the next, capped per leave type.

    Returns the number of ``to_year`` balances created/updated.
    """
    count = 0
    previous = LeaveBalance.objects.filter(
        tenant=tenant, year=from_year
    ).select_related("leave_type", "employee")
    for old in previous:
        lt = old.leave_type
        carry = ZERO
        if lt.allow_carry_forward:
            carry = min(old.available_days, lt.max_carry_forward_days)
            carry = max(carry, ZERO)
        new = get_or_create_balance(old.employee, lt, to_year)
        new.carried_forward_days = carry
        new.entitled_days = _entitlement_for(lt, to_year)
        new.save(update_fields=["carried_forward_days", "entitled_days", "updated_at"])
        count += 1
    return count


# --------------------------------------------------------------------------
# Conflict detection
# --------------------------------------------------------------------------
def overlapping_requests(employee, start: date, end: date, exclude_pk=None):
    """The employee's own pending/approved requests that clash with a range."""
    qs = LeaveRequest.objects.filter(
        tenant=employee.tenant,
        employee=employee,
        status__in=ACTIVE_STATUSES,
        start_date__lte=end,
        end_date__gte=start,
    )
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs


def team_conflicts(employee, start: date, end: date, exclude_pk=None):
    """Teammates with overlapping leave — drives non-blocking conflict warnings.

    A teammate is anyone in the same department, anyone reporting to the
    same line manager, or that line manager themselves.
    """
    from django.db.models import Q

    if employee.tenant_id is None:
        return LeaveRequest.objects.none()

    peer_filter = Q()
    matched = False
    if employee.department_id:
        peer_filter |= Q(employee__department_id=employee.department_id)
        matched = True
    if employee.line_manager_id:
        peer_filter |= Q(employee__line_manager_id=employee.line_manager_id)
        peer_filter |= Q(employee_id=employee.line_manager_id)
        matched = True
    if not matched:
        return LeaveRequest.objects.none()

    qs = (
        LeaveRequest.objects.filter(
            peer_filter,
            tenant=employee.tenant,
            status__in=ACTIVE_STATUSES,
            start_date__lte=end,
            end_date__gte=start,
        )
        .exclude(employee=employee)
    )
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs.select_related("employee", "leave_type")


# --------------------------------------------------------------------------
# Approval chain
# --------------------------------------------------------------------------
def _planned_stages(leave_type: LeaveType) -> list[tuple[str, str]]:
    """The (stage, label) chain a leave type requires, in order."""
    stages: list[tuple[str, str]] = [
        (ApprovalStage.MANAGER, "Line manager approval"),
    ]
    if leave_type.requires_hr_confirmation:
        stages.append((ApprovalStage.HR, "HR confirmation"))
    if leave_type.extra_approval_stage:
        label = leave_type.extra_approval_label or "Additional approval"
        stages.append((ApprovalStage.EXTRA, label))
    return stages


def build_approval_chain(leave_request: LeaveRequest) -> list[LeaveApproval]:
    """Create the ordered approval rows for a freshly submitted request."""
    leave_request.approvals.all().delete()
    rows = []
    for index, (stage, label) in enumerate(_planned_stages(leave_request.leave_type), start=1):
        rows.append(
            LeaveApproval.objects.create(
                tenant=leave_request.tenant,
                leave_request=leave_request,
                stage=stage,
                sequence=index,
                label=label,
            )
        )
    return rows


def _next_pending_approval(leave_request: LeaveRequest) -> LeaveApproval | None:
    return (
        leave_request.approvals.filter(status=ApprovalStatus.PENDING)
        .order_by("sequence")
        .first()
    )


# --------------------------------------------------------------------------
# Request lifecycle
# --------------------------------------------------------------------------
def validate_request(leave_request: LeaveRequest) -> None:
    """Apply the leave type's application rules. Raises on violation."""
    lt = leave_request.leave_type
    employee = leave_request.employee

    # Gender eligibility (maternity / paternity etc.).
    if lt.gender_eligibility != GenderEligibility.ANY:
        if (employee.gender or "") != lt.gender_eligibility:
            raise ValidationError(
                {"leave_type": f"This leave type is restricted to "
                               f"{lt.get_gender_eligibility_display().lower()}."}
            )

    days = working_days(
        leave_request.start_date,
        leave_request.end_date,
        leave_request.start_portion,
        leave_request.end_portion,
    )
    if days <= ZERO:
        raise ValidationError(
            {"start_date": "The requested range contains no working days."}
        )

    if lt.max_consecutive_days and days > lt.max_consecutive_days:
        raise ValidationError(
            {"end_date": f"This leave type allows at most "
                         f"{lt.max_consecutive_days} consecutive working days."}
        )

    if lt.min_notice_days:
        notice = (leave_request.start_date - timezone.now().date()).days
        if notice < lt.min_notice_days:
            raise ValidationError(
                {"start_date": f"This leave type requires at least "
                               f"{lt.min_notice_days} days' notice."}
            )

    if lt.requires_documentation and not leave_request.supporting_document:
        raise ValidationError(
            {"supporting_document": "A supporting document is required for this leave type."}
        )

    clash = overlapping_requests(
        employee, leave_request.start_date, leave_request.end_date,
        exclude_pk=leave_request.pk,
    ).first()
    if clash is not None:
        raise ValidationError(
            {"start_date": f"You already have leave ({clash.get_status_display()}) "
                           f"over {clash.start_date} – {clash.end_date}."}
        )


def submit_request(leave_request: LeaveRequest) -> LeaveRequest:
    """Move a draft request into the approval workflow.

    Computes the cost, reserves balance, builds the approval chain and
    notifies the first approver.
    """
    if leave_request.status not in {
        LeaveRequestStatus.DRAFT,
        LeaveRequestStatus.REJECTED,
    }:
        raise ValidationError("Only a draft request can be submitted.")

    validate_request(leave_request)

    leave_request.total_days = working_days(
        leave_request.start_date,
        leave_request.end_date,
        leave_request.start_portion,
        leave_request.end_portion,
    )

    balance = get_or_create_balance(
        leave_request.employee, leave_request.leave_type, leave_request.start_date.year
    )
    lt = leave_request.leave_type
    # Unpaid leave types and those allowing a negative balance are not capped.
    enforce_balance = lt.is_paid and not lt.allow_negative_balance
    if enforce_balance and leave_request.total_days > balance.available_days:
        raise ValidationError(
            {"total_days": f"Insufficient balance — {balance.available_days} "
                           f"day(s) available, {leave_request.total_days} requested."}
        )

    # Reserve the days against the balance.
    balance.pending_days += leave_request.total_days
    balance.save(update_fields=["pending_days", "updated_at"])

    leave_request.balance = balance
    leave_request.status = LeaveRequestStatus.PENDING
    leave_request.submitted_at = timezone.now()
    leave_request.decided_at = None
    leave_request.decision_note = ""

    if not lt.requires_approval:
        # Auto-approve leave types that need no sign-off.
        leave_request.current_stage = ""
        leave_request.save()
        return _finalise_approved(leave_request)

    build_approval_chain(leave_request)
    first = _next_pending_approval(leave_request)
    leave_request.current_stage = first.stage if first else ""
    leave_request.save()

    notify_event(
        leave_request,
        "submitted",
        f"{leave_request.employee} submitted a {lt.name} request "
        f"({leave_request.start_date} – {leave_request.end_date}).",
    )
    return leave_request


def _finalise_approved(leave_request: LeaveRequest) -> LeaveRequest:
    """Convert reserved pending days into taken days on full approval."""
    balance = leave_request.balance
    if balance is not None:
        balance.pending_days = max(ZERO, balance.pending_days - leave_request.total_days)
        balance.taken_days += leave_request.total_days
        balance.save(update_fields=["pending_days", "taken_days", "updated_at"])

    leave_request.status = LeaveRequestStatus.APPROVED
    leave_request.current_stage = ""
    leave_request.decided_at = timezone.now()
    leave_request.save(
        update_fields=["status", "current_stage", "decided_at", "updated_at"]
    )

    notify_event(
        leave_request,
        "approved",
        f"Leave for {leave_request.employee} ({leave_request.start_date} – "
        f"{leave_request.end_date}) was approved.",
    )
    if leave_request.leave_type.notify_finance:
        notify_finance(leave_request)
    return leave_request


def _release_balance(leave_request: LeaveRequest) -> None:
    """Return reserved pending days to the balance (reject / cancel)."""
    balance = leave_request.balance
    if balance is None:
        return
    balance.pending_days = max(ZERO, balance.pending_days - leave_request.total_days)
    balance.save(update_fields=["pending_days", "updated_at"])


def decide_stage(
    leave_request: LeaveRequest,
    *,
    approve: bool,
    user,
    comments: str = "",
) -> LeaveApproval:
    """Record a decision on the request's current approval stage.

    On approval of the final stage the request is approved and balance
    consumed; a rejection at any stage rejects the whole request and
    releases the reserved days.
    """
    if leave_request.status != LeaveRequestStatus.PENDING:
        raise ValidationError("This request is not awaiting approval.")

    approval = _next_pending_approval(leave_request)
    if approval is None:
        raise ValidationError("No approval stage is pending for this request.")

    approval.decided_by = user
    approval.decided_at = timezone.now()
    approval.comments = comments

    if not approve:
        approval.status = ApprovalStatus.REJECTED
        approval.save()
        leave_request.approvals.filter(status=ApprovalStatus.PENDING).update(
            status=ApprovalStatus.SKIPPED
        )
        _release_balance(leave_request)
        leave_request.status = LeaveRequestStatus.REJECTED
        leave_request.current_stage = ""
        leave_request.decided_at = timezone.now()
        leave_request.decision_note = comments[:255]
        leave_request.save(
            update_fields=[
                "status", "current_stage", "decided_at", "decision_note", "updated_at"
            ]
        )
        notify_event(
            leave_request,
            "rejected",
            f"Leave for {leave_request.employee} was rejected at the "
            f"{approval.get_stage_display()} stage.",
        )
        return approval

    approval.status = ApprovalStatus.APPROVED
    approval.save()

    nxt = _next_pending_approval(leave_request)
    if nxt is not None:
        leave_request.current_stage = nxt.stage
        leave_request.save(update_fields=["current_stage", "updated_at"])
        notify_event(
            leave_request,
            "stage_advanced",
            f"Leave for {leave_request.employee} advanced to the "
            f"{nxt.get_stage_display()} stage.",
        )
        return approval

    _finalise_approved(leave_request)
    return approval


def cancel_request(leave_request: LeaveRequest, *, by_owner: bool = True) -> LeaveRequest:
    """Cancel/withdraw a request and release any reserved or taken days."""
    if leave_request.status in {
        LeaveRequestStatus.CANCELLED,
        LeaveRequestStatus.WITHDRAWN,
        LeaveRequestStatus.REJECTED,
    }:
        raise ValidationError("This request is already closed.")

    balance = leave_request.balance
    if balance is not None:
        if leave_request.status == LeaveRequestStatus.APPROVED:
            balance.taken_days = max(ZERO, balance.taken_days - leave_request.total_days)
            balance.save(update_fields=["taken_days", "updated_at"])
        elif leave_request.status == LeaveRequestStatus.PENDING:
            _release_balance(leave_request)

    leave_request.approvals.filter(status=ApprovalStatus.PENDING).update(
        status=ApprovalStatus.SKIPPED
    )
    leave_request.status = (
        LeaveRequestStatus.WITHDRAWN if by_owner else LeaveRequestStatus.CANCELLED
    )
    leave_request.current_stage = ""
    leave_request.decided_at = timezone.now()
    leave_request.save(
        update_fields=["status", "current_stage", "decided_at", "updated_at"]
    )
    notify_event(
        leave_request,
        "cancelled",
        f"Leave for {leave_request.employee} ({leave_request.start_date} – "
        f"{leave_request.end_date}) was cancelled.",
    )
    return leave_request


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
# Internal leave-event name -> notification-engine event key.
_EVENT_KEYS = {
    "submitted": "leave_submitted",
    "stage_advanced": "leave_stage_advanced",
    "approved": "leave_approved",
    "rejected": "leave_rejected",
    "cancelled": "leave_cancelled",
}


def _leave_context(leave_request: LeaveRequest) -> dict:
    """Template context shared by every leave notification."""
    return {
        "employee_name": leave_request.employee.full_name,
        "leave_type": leave_request.leave_type.name,
        "start_date": str(leave_request.start_date),
        "end_date": str(leave_request.end_date),
        "total_days": str(leave_request.total_days),
        "note": leave_request.decision_note or "",
        "stage": leave_request.get_current_stage_display() or "",
    }


def _leave_recipients(leave_request: LeaveRequest, event: str) -> list:
    """Resolve the user accounts to notify for a leave event."""
    employee_user = getattr(leave_request.employee, "user", None)
    manager = leave_request.employee.line_manager
    manager_user = getattr(manager, "user", None) if manager else None
    if event == "submitted":
        return [manager_user]
    if event in {"rejected", "stage_advanced"}:
        return [employee_user]
    return [employee_user, manager_user]  # approved / cancelled


def notify_event(leave_request: LeaveRequest, event: str, message: str = "") -> None:
    """Raise a leave notification through the notification engine.

    ``message`` is retained for call-site readability; the engine renders
    the tenant's template instead.
    """
    event_key = _EVENT_KEYS.get(event)
    if event_key is None:
        return
    from apps.notifications import services as notifications

    notifications.dispatch(
        tenant=leave_request.tenant,
        event_key=event_key,
        users=_leave_recipients(leave_request, event),
        context=_leave_context(leave_request),
        entity_type="leave.leave_request",
        entity_id=str(leave_request.pk),
    )


def notify_finance(leave_request: LeaveRequest) -> None:
    """Notify the tenant's configured Accounts/Finance recipients on approval."""
    tenant_settings = getattr(leave_request.tenant, "settings", None)
    extra = []
    if tenant_settings is not None:
        extra = list(
            (tenant_settings.notification_recipients or {}).get(
                "leave_finance_notice", []
            )
        )
    from apps.notifications import services as notifications

    notifications.dispatch(
        tenant=leave_request.tenant,
        event_key="leave_finance_notice",
        extra_emails=extra,
        context=_leave_context(leave_request),
        entity_type="leave.leave_request",
        entity_id=str(leave_request.pk),
    )
