"""Policies & Acknowledgements business logic (spec §9.24).

Policies are versioned: a draft :class:`PolicyVersion` is published,
which flips the policy's ``current_version`` and resets every
assignment's ack so employees re-read the new version.
``assign_policy`` / ``bulk_assign`` is idempotent — assigning the same
employee twice updates the existing row rather than duplicating it.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.employees.models import Employee

from .enums import AssignmentStatus
from .models import Policy, PolicyAssignment, PolicyVersion


# --- notifications --------------------------------------------------------

def _dispatch(event_key: str, *, tenant, user, policy: Policy, **context):
    """Defensive notification dispatch — never blocks a state transition."""
    if user is None:
        return
    from apps.notifications import services as notifications

    notifications.dispatch(
        tenant=tenant,
        event_key=event_key,
        users=[user],
        context={
            "policy_title": policy.title,
            "policy_code": policy.code,
            "policy_version": (
                policy.current_version.version if policy.current_version else ""
            ),
            **context,
        },
        entity_type="policies.policy",
        entity_id=str(policy.pk),
    )


# --- version lifecycle ----------------------------------------------------

@transaction.atomic
def publish_version(version: PolicyVersion, *, user=None) -> PolicyVersion:
    """Publish a draft version, flip ``current_version`` and reset acks.

    Notifies every assignee that a new version is live — they must
    re-acknowledge.
    """
    if version.published_at is not None:
        raise ValidationError("This version is already published.")

    version.published_at = timezone.now()
    version.published_by = user if user and user.is_authenticated else None
    version.save(update_fields=["published_at", "published_by", "updated_at"])

    policy = version.policy
    previous_current = policy.current_version_id
    policy.current_version = version
    policy.save(update_fields=["current_version", "updated_at"])

    # Reset acknowledgements so employees re-read the new version.
    if previous_current and previous_current != version.pk:
        assignments = PolicyAssignment.objects.filter(
            tenant=policy.tenant, policy=policy
        ).exclude(acknowledged_at__isnull=True)
        for assignment in assignments:
            assignment.acknowledged_at = None
            assignment.acknowledged_version = None
            assignment.save(update_fields=[
                "acknowledged_at", "acknowledged_version", "updated_at",
            ])
            _dispatch(
                "policy_published",
                tenant=policy.tenant,
                user=getattr(assignment.employee, "user", None),
                policy=policy,
            )
    return version


# --- assignment lifecycle -------------------------------------------------

def assign_policy(
    *, tenant, policy: Policy, employee: Employee,
    due_date: date | None = None, assigned_by=None, notify: bool = True,
) -> PolicyAssignment:
    """Assign a policy to a single employee. Idempotent on (policy, employee)."""
    assignment, created = PolicyAssignment.objects.get_or_create(
        tenant=tenant, policy=policy, employee=employee,
        defaults={
            "due_date": due_date,
            "assigned_by": assigned_by if (
                assigned_by and assigned_by.is_authenticated
            ) else None,
        },
    )
    if not created and due_date and assignment.due_date != due_date:
        assignment.due_date = due_date
        assignment.save(update_fields=["due_date", "updated_at"])
    if created and notify:
        _dispatch(
            "policy_assigned",
            tenant=tenant,
            user=getattr(employee, "user", None),
            policy=policy,
            due_date=due_date.isoformat() if due_date else "",
        )
    return assignment


def bulk_assign(
    *, tenant, policy: Policy, employees: Iterable[Employee],
    due_date: date | None = None, assigned_by=None,
) -> list[PolicyAssignment]:
    """Assign a policy to many employees. Returns the assignment rows."""
    return [
        assign_policy(
            tenant=tenant, policy=policy, employee=emp,
            due_date=due_date, assigned_by=assigned_by,
        )
        for emp in employees
    ]


def acknowledge(
    assignment: PolicyAssignment, *, user=None, comment: str = "",
) -> PolicyAssignment:
    """Mark the assignment acknowledged against the current policy version."""
    policy = assignment.policy
    if policy.current_version is None:
        raise ValidationError(
            "This policy has no published version to acknowledge."
        )
    assignment.acknowledged_at = timezone.now()
    assignment.acknowledged_version = policy.current_version
    if comment:
        assignment.comment = comment
    assignment.save(update_fields=[
        "acknowledged_at", "acknowledged_version", "comment", "updated_at",
    ])
    return assignment


# --- queries --------------------------------------------------------------

def assignment_status(assignment: PolicyAssignment) -> str:
    return (
        AssignmentStatus.ACKNOWLEDGED
        if assignment.acknowledged_at is not None
        else AssignmentStatus.PENDING
    )


def pending_assignments_for(employee: Employee):
    """Active policies the employee still needs to acknowledge."""
    return PolicyAssignment.objects.filter(
        tenant=employee.tenant,
        employee=employee,
        acknowledged_at__isnull=True,
        policy__is_active=True,
    ).select_related("policy", "policy__current_version")
