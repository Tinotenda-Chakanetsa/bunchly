"""Workflow-engine models (spec §10).

A generic, tenant-configurable approval engine. Domain modules attach to
it rather than re-implementing approval chains:

``Workflow``          a definition for one entity type (e.g. a leave
                      workflow) — a reusable template.
``WorkflowStage``     a configurable, ordered approval stage; its
                      approver is resolved at run time by role, named
                      user, line manager or department head.
``WorkflowInstance``  a workflow running against one domain object.
``WorkflowAction``    an append-only log of every decision / comment.

Stages are never hard-coded — a tenant builds its own chains.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import (
    ApproverType,
    WorkflowActionType,
    WorkflowEntity,
    WorkflowStatus,
)


class Workflow(TenantOwnedModel):
    """A reusable approval-chain definition for one entity type."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    description = models.TextField(blank=True)
    entity_type = models.CharField(
        max_length=24, choices=WorkflowEntity.choices, db_index=True
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Used when a domain object of this type needs a workflow.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["entity_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_workflow_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "entity_type", "is_active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_entity_type_display()})"


class WorkflowStage(TenantOwnedModel):
    """One configurable approval stage within a workflow.

    The approver is resolved at run time from ``approver_type`` — by role,
    a named user, or the subject employee's line manager / department head.
    """

    workflow = models.ForeignKey(
        Workflow, on_delete=models.CASCADE, related_name="stages"
    )
    name = models.CharField(max_length=120)
    sequence = models.PositiveSmallIntegerField(
        help_text="Order within the workflow — lower decides first."
    )
    approver_type = models.CharField(
        max_length=20, choices=ApproverType.choices, default=ApproverType.ROLE
    )
    approver_role = models.ForeignKey(
        "accounts.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_stages",
        help_text="Required when approver type is 'role'.",
    )
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_stages",
        help_text="Required when approver type is 'named user'.",
    )
    sla_days = models.PositiveIntegerField(
        default=0, help_text="Days before the stage is escalated; 0 = no SLA."
    )
    allow_request_info = models.BooleanField(
        default=True, help_text="Approver may send the item back for more info."
    )

    class Meta:
        ordering = ["workflow", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "sequence"],
                name="uniq_workflowstage_sequence_per_workflow",
            )
        ]
        indexes = [models.Index(fields=["tenant", "workflow"])]

    def __str__(self) -> str:
        return f"{self.workflow.name} · {self.sequence}. {self.name}"


class WorkflowInstance(TenantOwnedModel):
    """A workflow running against one domain object.

    ``entity_type`` / ``entity_id`` are a loose reference to the governed
    record (no hard FK — the engine spans modules). ``subject_employee``
    is set when the workflow concerns a person, so line-manager and
    department-head approver stages can resolve.
    """

    workflow = models.ForeignKey(
        Workflow, on_delete=models.PROTECT, related_name="instances"
    )
    entity_type = models.CharField(max_length=80, blank=True, db_index=True)
    entity_id = models.CharField(max_length=64, blank=True, db_index=True)
    subject = models.CharField(
        max_length=200, help_text="Human-readable label for the item."
    )
    subject_employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_instances",
    )

    status = models.CharField(
        max_length=20,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.DRAFT,
        db_index=True,
    )
    current_stage = models.ForeignKey(
        WorkflowStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_workflows",
    )
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot data for notification rendering / display.",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    # When the current stage was entered — basis for SLA escalation.
    stage_entered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "entity_type", "entity_id"]),
            models.Index(fields=["tenant", "current_stage", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.subject} [{self.get_status_display()}]"


class WorkflowAction(TenantOwnedModel):
    """An append-only record of one action taken on a workflow instance."""

    instance = models.ForeignKey(
        WorkflowInstance, on_delete=models.CASCADE, related_name="actions"
    )
    stage = models.ForeignKey(
        WorkflowStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    action = models.CharField(max_length=20, choices=WorkflowActionType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["tenant", "instance", "created_at"])]

    def __str__(self) -> str:
        return f"{self.get_action_display()} — {self.instance.subject}"
