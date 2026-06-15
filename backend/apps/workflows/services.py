"""Workflow-engine business logic (spec §10).

The engine is generic: it advances a ``WorkflowInstance`` through its
``WorkflowStage`` chain, resolves each stage's approvers at run time,
records every action and dispatches notifications. Domain modules call
``start_instance`` / ``submit_instance`` / ``act`` — they never touch
status fields directly.
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.notifications import services as notifications
from apps.notifications.enums import NotificationType

from .enums import (
    ApproverType,
    OPEN_STATUSES,
    WorkflowActionType,
    WorkflowStatus,
)
from .models import Workflow, WorkflowAction, WorkflowInstance, WorkflowStage


# --------------------------------------------------------------------------
# Approver resolution
# --------------------------------------------------------------------------
def resolve_approvers(stage: WorkflowStage, instance: WorkflowInstance) -> list:
    """Resolve the user accounts authorised to decide a stage.

    Resolution is dynamic so a workflow definition stays valid as people
    move roles or reporting lines.
    """
    if stage is None:
        return []
    tenant = instance.tenant

    if stage.approver_type == ApproverType.NAMED_USER:
        return [stage.approver_user] if stage.approver_user_id else []

    if stage.approver_type == ApproverType.ROLE:
        if not stage.approver_role_id:
            return []
        from apps.accounts.models import User

        return list(
            User.objects.filter(
                memberships__tenant=tenant,
                memberships__roles=stage.approver_role,
                memberships__is_active=True,
                is_active=True,
            ).distinct()
        )

    employee = instance.subject_employee
    if employee is None:
        return []
    if stage.approver_type == ApproverType.LINE_MANAGER:
        manager = employee.line_manager
        user = getattr(manager, "user", None) if manager else None
        return [user] if user else []
    if stage.approver_type == ApproverType.DEPARTMENT_HEAD:
        department = employee.department
        head = getattr(department, "head", None) if department else None
        user = getattr(head, "user", None) if head else None
        return [user] if user else []
    return []


def can_user_act(user, instance: WorkflowInstance) -> bool:
    """Whether ``user`` may decide the instance's current stage."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_platform_admin", False):
        return True
    tenant = instance.tenant
    if user.has_perm_code("workflows.view", tenant):
        return True  # HR / org-wide approver oversight
    approvers = resolve_approvers(instance.current_stage, instance)
    return any(u.pk == user.pk for u in approvers)


# --------------------------------------------------------------------------
# Stage navigation
# --------------------------------------------------------------------------
def _ordered_stages(workflow: Workflow) -> list[WorkflowStage]:
    return list(workflow.stages.order_by("sequence"))


def _next_stage(instance: WorkflowInstance) -> WorkflowStage | None:
    if instance.current_stage is None:
        return None
    return (
        instance.workflow.stages.filter(
            sequence__gt=instance.current_stage.sequence
        )
        .order_by("sequence")
        .first()
    )


def _log(instance, action, *, actor=None, comment="", stage=None) -> WorkflowAction:
    return WorkflowAction.objects.create(
        tenant=instance.tenant,
        instance=instance,
        stage=stage or instance.current_stage,
        action=action,
        actor=actor,
        comment=comment,
    )


def _context(instance: WorkflowInstance, *, actor=None, comment="") -> dict:
    """Template context for a workflow notification."""
    stage = instance.current_stage
    return {
        "subject": instance.subject,
        "stage": stage.name if stage else "",
        "sla_days": stage.sla_days if stage else 0,
        "status": instance.get_status_display(),
        "actor_name": getattr(actor, "full_name", "") or "",
        "comment": comment or "",
    }


def _notify(instance, event_key, users, *, actor=None, comment="") -> None:
    notifications.dispatch(
        tenant=instance.tenant,
        event_key=event_key,
        users=[u for u in users if u is not None],
        context=_context(instance, actor=actor, comment=comment),
        entity_type="workflows.workflow_instance",
        entity_id=str(instance.pk),
    )


# --------------------------------------------------------------------------
# Lifecycle
# --------------------------------------------------------------------------
def start_instance(
    *,
    workflow: Workflow,
    subject: str,
    initiated_by=None,
    entity_type: str = "",
    entity_id: str = "",
    subject_employee=None,
    context: dict | None = None,
) -> WorkflowInstance:
    """Create a draft workflow instance for a domain object."""
    return WorkflowInstance.objects.create(
        tenant=workflow.tenant,
        workflow=workflow,
        subject=subject,
        entity_type=entity_type,
        entity_id=str(entity_id),
        subject_employee=subject_employee,
        initiated_by=initiated_by,
        context=context or {},
        status=WorkflowStatus.DRAFT,
    )


def submit_instance(instance: WorkflowInstance, *, actor=None) -> WorkflowInstance:
    """Submit a draft instance into its approval chain."""
    if instance.status != WorkflowStatus.DRAFT:
        raise ValidationError("Only a draft workflow can be submitted.")
    stages = _ordered_stages(instance.workflow)
    if not stages:
        raise ValidationError("This workflow has no stages configured.")

    now = timezone.now()
    instance.current_stage = stages[0]
    instance.status = WorkflowStatus.PENDING_APPROVAL
    instance.submitted_at = now
    instance.stage_entered_at = now
    instance.save(
        update_fields=[
            "current_stage", "status", "submitted_at",
            "stage_entered_at", "updated_at",
        ]
    )
    _log(instance, WorkflowActionType.SUBMIT, actor=actor)
    _notify(
        instance,
        NotificationType.WORKFLOW_SUBMITTED,
        resolve_approvers(instance.current_stage, instance),
        actor=actor,
    )
    return instance


def _finalise(instance, status, *, actor, comment) -> WorkflowInstance:
    instance.status = status
    instance.completed_at = timezone.now()
    instance.save(update_fields=["status", "completed_at", "updated_at"])
    return instance


def act(
    instance: WorkflowInstance,
    *,
    action: str,
    actor=None,
    comment: str = "",
) -> WorkflowInstance:
    """Apply a decision to an instance and advance the workflow.

    Handles approve / reject / request-info / provide-info / cancel /
    comment / complete; raises if the action is invalid for the state.
    """
    if action == WorkflowActionType.COMMENT:
        _log(instance, action, actor=actor, comment=comment)
        return instance

    if action == WorkflowActionType.CANCEL:
        if instance.status in {
            WorkflowStatus.CANCELLED, WorkflowStatus.COMPLETED,
            WorkflowStatus.REJECTED,
        }:
            raise ValidationError("This workflow is already closed.")
        _log(instance, action, actor=actor, comment=comment)
        return _finalise(
            instance, WorkflowStatus.CANCELLED, actor=actor, comment=comment
        )

    if instance.status not in OPEN_STATUSES:
        raise ValidationError("This workflow is not open for decisions.")

    if action == WorkflowActionType.APPROVE:
        _log(instance, action, actor=actor, comment=comment)
        nxt = _next_stage(instance)
        if nxt is not None:
            instance.current_stage = nxt
            instance.status = WorkflowStatus.PENDING_APPROVAL
            instance.stage_entered_at = timezone.now()
            instance.save(
                update_fields=[
                    "current_stage", "status", "stage_entered_at", "updated_at"
                ]
            )
            _notify(
                instance, NotificationType.WORKFLOW_SUBMITTED,
                resolve_approvers(nxt, instance), actor=actor,
            )
            return instance
        _finalise(instance, WorkflowStatus.APPROVED, actor=actor, comment=comment)
        _notify(
            instance, NotificationType.WORKFLOW_APPROVED,
            [instance.initiated_by], actor=actor, comment=comment,
        )
        return instance

    if action == WorkflowActionType.REJECT:
        _log(instance, action, actor=actor, comment=comment)
        _finalise(instance, WorkflowStatus.REJECTED, actor=actor, comment=comment)
        _notify(
            instance, NotificationType.WORKFLOW_REJECTED,
            [instance.initiated_by], actor=actor, comment=comment,
        )
        return instance

    if action == WorkflowActionType.REQUEST_INFO:
        if instance.current_stage and not instance.current_stage.allow_request_info:
            raise ValidationError(
                "This stage does not allow requesting more information."
            )
        instance.status = WorkflowStatus.MORE_INFO
        instance.save(update_fields=["status", "updated_at"])
        _log(instance, action, actor=actor, comment=comment)
        _notify(
            instance, NotificationType.WORKFLOW_INFO_REQUESTED,
            [instance.initiated_by], actor=actor, comment=comment,
        )
        return instance

    if action == WorkflowActionType.PROVIDE_INFO:
        if instance.status != WorkflowStatus.MORE_INFO:
            raise ValidationError("No information has been requested.")
        instance.status = WorkflowStatus.PENDING_APPROVAL
        instance.stage_entered_at = timezone.now()
        instance.save(
            update_fields=["status", "stage_entered_at", "updated_at"]
        )
        _log(instance, action, actor=actor, comment=comment)
        _notify(
            instance, NotificationType.WORKFLOW_SUBMITTED,
            resolve_approvers(instance.current_stage, instance), actor=actor,
        )
        return instance

    if action == WorkflowActionType.COMPLETE:
        _log(instance, action, actor=actor, comment=comment)
        _finalise(instance, WorkflowStatus.COMPLETED, actor=actor, comment=comment)
        _notify(
            instance, NotificationType.WORKFLOW_COMPLETED,
            [instance.initiated_by], actor=actor,
        )
        return instance

    raise ValidationError(f"Unsupported workflow action '{action}'.")


# --------------------------------------------------------------------------
# Escalation
# --------------------------------------------------------------------------
def escalate_overdue(tenant=None, *, now=None) -> int:
    """Escalate instances stuck on an SLA-bound stage past its window.

    Each stage entry is escalated at most once. Returns the count sent.
    """
    now = now or timezone.now()
    queryset = WorkflowInstance.objects.filter(
        status=WorkflowStatus.PENDING_APPROVAL,
        current_stage__isnull=False,
        current_stage__sla_days__gt=0,
        stage_entered_at__isnull=False,
    ).select_related("current_stage", "workflow", "subject_employee", "initiated_by")
    if tenant is not None:
        queryset = queryset.filter(tenant=tenant)

    escalated = 0
    for instance in queryset:
        stage = instance.current_stage
        deadline = instance.stage_entered_at + timedelta(days=stage.sla_days)
        if now < deadline:
            continue
        already = instance.actions.filter(
            action=WorkflowActionType.ESCALATE,
            stage=stage,
            created_at__gte=instance.stage_entered_at,
        ).exists()
        if already:
            continue
        _log(instance, WorkflowActionType.ESCALATE, comment="SLA exceeded.")
        _notify(
            instance, NotificationType.WORKFLOW_ESCALATED,
            resolve_approvers(stage, instance),
        )
        escalated += 1
    return escalated
