"""Onboarding / offboarding models (spec §9.6, §9.7).

``ChecklistTemplate`` + ``ChecklistTaskTemplate`` are the configurable
per-tenant checklists. ``OnboardingProgramme`` + ``OnboardingTask`` are
the running instance assigned to an employee — one programme covers
either an onboarding or an offboarding run, with tasks routed to HR /
IT / Finance / Manager / Employee owners.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import (
    ProgrammeStatus,
    ProgrammeType,
    TaskOwnerRole,
    TaskStatus,
)


class ChecklistTemplate(TenantOwnedModel):
    """A configurable onboarding / offboarding checklist."""

    name = models.CharField(max_length=160)
    programme_type = models.CharField(
        max_length=12, choices=ProgrammeType.choices, default=ProgrammeType.ONBOARDING
    )
    description = models.TextField(blank=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Used by default for new programmes of this type.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["programme_type", "name"]
        indexes = [models.Index(fields=["tenant", "programme_type", "is_active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_programme_type_display()})"


class ChecklistTaskTemplate(TenantOwnedModel):
    """A task line within a checklist template."""

    template = models.ForeignKey(
        ChecklistTemplate, on_delete=models.CASCADE, related_name="task_templates"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner_role = models.CharField(
        max_length=10, choices=TaskOwnerRole.choices, default=TaskOwnerRole.HR
    )
    sequence = models.PositiveSmallIntegerField(default=1)
    due_offset_days = models.IntegerField(
        default=0,
        help_text="Days from the programme start date the task is due.",
    )

    class Meta:
        ordering = ["template", "sequence"]
        indexes = [models.Index(fields=["tenant", "template"])]

    def __str__(self) -> str:
        return f"{self.template.name} · {self.sequence}. {self.title}"


class OnboardingProgramme(TenantOwnedModel):
    """A running onboarding / offboarding programme for one employee."""

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="onboarding_programmes",
    )
    programme_type = models.CharField(
        max_length=12, choices=ProgrammeType.choices, default=ProgrammeType.ONBOARDING
    )
    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programmes",
    )
    status = models.CharField(
        max_length=12,
        choices=ProgrammeStatus.choices,
        default=ProgrammeStatus.NOT_STARTED,
        db_index=True,
    )
    start_date = models.DateField(null=True, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "employee", "programme_type"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_programme_type_display()} — {self.employee}"


class OnboardingTask(TenantOwnedModel):
    """A single task within a running programme."""

    programme = models.ForeignKey(
        OnboardingProgramme, on_delete=models.CASCADE, related_name="tasks"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner_role = models.CharField(
        max_length=10, choices=TaskOwnerRole.choices, default=TaskOwnerRole.HR
    )
    assigned_to = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_onboarding_tasks",
        help_text="The specific person responsible, if named.",
    )
    sequence = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(
        max_length=12,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        db_index=True,
    )
    due_date = models.DateField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["programme", "sequence"]
        indexes = [
            models.Index(fields=["tenant", "programme", "status"]),
            models.Index(fields=["tenant", "assigned_to", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"
