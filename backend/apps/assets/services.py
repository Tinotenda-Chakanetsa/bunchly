"""Asset-management business logic (spec §9.23).

Keeps an asset's ``status`` in step with its assignments: issuing an
asset marks it assigned, returning it makes it available again, and a
lost report flags it. ``pending_returns`` powers the offboarding
asset-return checklist.
"""
from __future__ import annotations

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .enums import ASSIGNABLE_STATUSES, AssetStatus, AssignmentStatus
from .models import Asset, AssetAssignment


def assign_asset(
    *,
    tenant,
    asset: Asset,
    employee,
    issued_by=None,
    issued_date=None,
    due_return_date=None,
    issue_condition: str = "",
    notes: str = "",
) -> AssetAssignment:
    """Issue an asset to an employee, marking the asset assigned."""
    if asset.status not in ASSIGNABLE_STATUSES:
        raise ValidationError(
            f"Asset '{asset.asset_tag}' is {asset.get_status_display().lower()} "
            f"and cannot be assigned."
        )
    assignment = AssetAssignment.objects.create(
        tenant=tenant,
        asset=asset,
        employee=employee,
        status=AssignmentStatus.ISSUED,
        issued_by=issued_by,
        issued_date=issued_date or timezone.now().date(),
        due_return_date=due_return_date,
        issue_condition=issue_condition or asset.condition,
        notes=notes,
    )
    asset.status = AssetStatus.ASSIGNED
    asset.save(update_fields=["status", "updated_at"])
    return assignment


def return_asset(
    assignment: AssetAssignment,
    *,
    returned_to=None,
    return_condition: str = "",
    returned_date=None,
    notes: str = "",
) -> AssetAssignment:
    """Record the return of an issued asset, freeing it for re-issue."""
    if assignment.status != AssignmentStatus.ISSUED:
        raise ValidationError("Only an issued assignment can be returned.")
    assignment.status = AssignmentStatus.RETURNED
    assignment.returned_date = returned_date or timezone.now().date()
    assignment.returned_to = returned_to
    if return_condition:
        assignment.return_condition = return_condition
    if notes:
        assignment.notes = notes
    assignment.save(update_fields=[
        "status", "returned_date", "returned_to", "return_condition",
        "notes", "updated_at",
    ])

    asset = assignment.asset
    asset.status = AssetStatus.AVAILABLE
    if return_condition:
        asset.condition = return_condition
    asset.save(update_fields=["status", "condition", "updated_at"])
    return assignment


def report_lost(assignment: AssetAssignment, *, notes: str = "") -> AssetAssignment:
    """Flag an issued asset as lost while assigned."""
    if assignment.status != AssignmentStatus.ISSUED:
        raise ValidationError("Only an issued assignment can be reported lost.")
    assignment.status = AssignmentStatus.LOST
    if notes:
        assignment.notes = notes
    assignment.save(update_fields=["status", "notes", "updated_at"])

    asset = assignment.asset
    asset.status = AssetStatus.LOST
    asset.save(update_fields=["status", "updated_at"])
    return assignment


def pending_returns(employee):
    """An employee's still-issued assets — the offboarding return checklist."""
    return AssetAssignment.objects.filter(
        tenant=employee.tenant,
        employee=employee,
        status=AssignmentStatus.ISSUED,
    ).select_related("asset", "asset__category")
