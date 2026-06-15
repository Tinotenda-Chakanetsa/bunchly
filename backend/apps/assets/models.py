"""Asset-management models (spec §9.23).

``AssetCategory``    configurable asset types (laptop, phone, ID card …).
``Asset``            a tracked company asset with status and condition.
``AssetAssignment``  an asset issued to an employee — issue / return
                     dates and condition, feeding the offboarding
                     asset-return checklist.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import AssetCondition, AssetStatus, AssignmentStatus

ZERO = Decimal("0.00")


class AssetCategory(TenantOwnedModel):
    """A configurable asset type (spec §9.23 — laptop, phone, keys …)."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Asset categories"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_assetcategory_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return self.name


class Asset(TenantOwnedModel):
    """A tracked company asset."""

    category = models.ForeignKey(
        AssetCategory, on_delete=models.PROTECT, related_name="assets"
    )
    name = models.CharField(max_length=200)
    asset_tag = models.CharField(max_length=60, db_index=True)
    serial_number = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=AssetStatus.choices,
        default=AssetStatus.AVAILABLE,
        db_index=True,
    )
    condition = models.CharField(
        max_length=10, choices=AssetCondition.choices, default=AssetCondition.GOOD
    )
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO
    )
    currency = models.CharField(max_length=3, default="GBP")
    location = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "asset_tag"], name="uniq_asset_tag_per_tenant"
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.asset_tag})"


class AssetAssignment(TenantOwnedModel):
    """An asset issued to an employee (spec §9.23)."""

    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name="assignments"
    )
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="asset_assignments"
    )
    status = models.CharField(
        max_length=10,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ISSUED,
        db_index=True,
    )
    issued_date = models.DateField()
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    issue_condition = models.CharField(
        max_length=10, choices=AssetCondition.choices, default=AssetCondition.GOOD
    )
    due_return_date = models.DateField(null=True, blank=True)
    returned_date = models.DateField(null=True, blank=True)
    return_condition = models.CharField(
        max_length=10, choices=AssetCondition.choices, blank=True
    )
    returned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-issued_date"]
        indexes = [
            models.Index(fields=["tenant", "employee", "status"]),
            models.Index(fields=["tenant", "asset", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.asset} → {self.employee} ({self.get_status_display()})"
