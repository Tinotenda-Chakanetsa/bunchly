"""Onboarding / offboarding business logic (spec §9.6, §9.7).

Builds a running programme from a checklist template, drives the task
lifecycle and keeps the programme status in step with its tasks.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .enums import (
    ProgrammeStatus,
    ProgrammeType,
    RESOLVED_TASK_STATUSES,
    TaskStatus,
)
from .models import (
    ChecklistTemplate,
    OnboardingProgramme,
    OnboardingTask,
)


def default_template(tenant, programme_type: str) -> ChecklistTemplate | None:
    """The default active checklist for a programme type, if one is set."""
    return (
        ChecklistTemplate.objects.filter(
            tenant=tenant, programme_type=programme_type, is_active=True
        )
        .order_by("-is_default", "name")
        .first()
    )


def start_programme(
    *,
    tenant,
    employee,
    programme_type: str = ProgrammeType.ONBOARDING,
    template: ChecklistTemplate | None = None,
    start_date: date | None = None,
    notes: str = "",
) -> OnboardingProgramme:
    """Create a programme for an employee and instantiate its tasks.

    Tasks are copied from the template (or the tenant default for the
    type); each task's due date is the start date plus its template
    offset.
    """
    start_date = start_date or timezone.now().date()
    if template is None:
        template = default_template(tenant, programme_type)

    programme = OnboardingProgramme.objects.create(
        tenant=tenant,
        employee=employee,
        programme_type=programme_type,
        template=template,
        status=ProgrammeStatus.IN_PROGRESS,
        start_date=start_date,
        notes=notes,
    )

    if template is not None:
        task_templates = template.task_templates.order_by("sequence")
        last_offset = 0
        for task_template in task_templates:
            OnboardingTask.objects.create(
                tenant=tenant,
                programme=programme,
                title=task_template.title,
                description=task_template.description,
                owner_role=task_template.owner_role,
                sequence=task_template.sequence,
                due_date=start_date + timedelta(days=task_template.due_offset_days),
            )
            last_offset = max(last_offset, task_template.due_offset_days)
        if task_templates.exists():
            programme.target_completion_date = start_date + timedelta(days=last_offset)
            programme.save(update_fields=["target_completion_date", "updated_at"])
    return programme


def set_task_status(task: OnboardingTask, status: str, *, user=None, notes: str = "") -> OnboardingTask:
    """Update a task's status and keep its programme status in step."""
    if status not in TaskStatus.values:
        raise ValidationError({"status": f"Invalid task status '{status}'."})
    task.status = status
    if notes:
        task.notes = notes
    if status == TaskStatus.COMPLETED:
        task.completed_at = timezone.now()
        task.completed_by = user
    else:
        task.completed_at = None
        task.completed_by = None
    task.save(update_fields=[
        "status", "notes", "completed_at", "completed_by", "updated_at",
    ])
    recalculate_programme(task.programme)
    return task


def recalculate_programme(programme: OnboardingProgramme) -> OnboardingProgramme:
    """Mark a programme completed once every task is resolved."""
    if programme.status == ProgrammeStatus.CANCELLED:
        return programme
    tasks = list(programme.tasks.all())
    if tasks and all(t.status in RESOLVED_TASK_STATUSES for t in tasks):
        if programme.status != ProgrammeStatus.COMPLETED:
            programme.status = ProgrammeStatus.COMPLETED
            programme.completed_at = timezone.now()
            programme.save(update_fields=["status", "completed_at", "updated_at"])
    elif programme.status == ProgrammeStatus.COMPLETED:
        # A task was reopened — the programme is in progress again.
        programme.status = ProgrammeStatus.IN_PROGRESS
        programme.completed_at = None
        programme.save(update_fields=["status", "completed_at", "updated_at"])
    return programme


def cancel_programme(programme: OnboardingProgramme) -> OnboardingProgramme:
    """Cancel a programme that has not completed."""
    if programme.status == ProgrammeStatus.COMPLETED:
        raise ValidationError("A completed programme cannot be cancelled.")
    programme.status = ProgrammeStatus.CANCELLED
    programme.save(update_fields=["status", "updated_at"])
    return programme


def programme_progress(programme: OnboardingProgramme) -> dict:
    """Task completion statistics for a programme."""
    tasks = list(programme.tasks.all())
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    resolved = sum(1 for t in tasks if t.status in RESOLVED_TASK_STATUSES)
    overdue = sum(
        1
        for t in tasks
        if t.due_date
        and t.due_date < timezone.now().date()
        and t.status not in RESOLVED_TASK_STATUSES
    )
    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "resolved_tasks": resolved,
        "overdue_tasks": overdue,
        "percent_complete": round((resolved / total) * 100, 1) if total else 0.0,
    }
