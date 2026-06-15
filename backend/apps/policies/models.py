"""Policies & Acknowledgements models (spec §9.24).

Three pieces:

``Policy``              the catalogue entry — title, category, owner, and
                        a pointer to the current published version.
``PolicyVersion``       a versioned document upload. Versions are drafted
                        and published; publishing flips the policy's
                        ``current_version`` and resets assignment acks.
``PolicyAssignment``    one row per (policy, employee) — tracks who must
                        acknowledge and who already has, with the version
                        they acknowledged.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import PolicyCategory


class Policy(TenantOwnedModel):
    """A policy that may require employee acknowledgement."""

    title = models.CharField(max_length=200)
    code = models.CharField(max_length=40)
    category = models.CharField(
        max_length=30, choices=PolicyCategory.choices,
        default=PolicyCategory.HR_POLICY, db_index=True,
    )
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        "employees.Employee", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="owned_policies",
    )
    requires_acknowledgement = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, db_index=True)
    current_version = models.ForeignKey(
        "policies.PolicyVersion", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )

    class Meta:
        ordering = ["title"]
        verbose_name_plural = "policies"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_policy_code_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
            models.Index(fields=["tenant", "category"]),
        ]

    def __str__(self) -> str:
        return self.title


class PolicyVersion(TenantOwnedModel):
    """A versioned policy document — drafted, then published."""

    policy = models.ForeignKey(
        Policy, on_delete=models.CASCADE, related_name="versions",
    )
    version = models.CharField(max_length=30, help_text="e.g. 1.0, 2.1")
    document = models.FileField(upload_to="policies/", null=True, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    change_summary = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["policy", "version"],
                name="uniq_policy_version_per_policy",
            ),
        ]
        indexes = [models.Index(fields=["tenant", "policy"])]

    def __str__(self) -> str:
        return f"{self.policy.title} v{self.version}"

    @property
    def is_published(self) -> bool:
        return self.published_at is not None


class PolicyAssignment(TenantOwnedModel):
    """A requirement that ``employee`` acknowledges ``policy``.

    One row per (policy, employee). Tracks the version the employee
    acknowledged — when a new version is published, ``acknowledged_at``
    and ``acknowledged_version`` are reset so the employee re-acks.
    """

    policy = models.ForeignKey(
        Policy, on_delete=models.CASCADE, related_name="assignments",
    )
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE,
        related_name="policy_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    due_date = models.DateField(null=True, blank=True, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True, db_index=True)
    acknowledged_version = models.ForeignKey(
        PolicyVersion, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="acknowledgements",
    )
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["policy", "employee"],
                name="uniq_policy_per_employee",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "employee", "acknowledged_at"]),
            models.Index(fields=["tenant", "policy", "acknowledged_at"]),
        ]

    def __str__(self) -> str:
        state = "acknowledged" if self.acknowledged_at else "pending"
        return f"{self.employee} — {self.policy} ({state})"

    @property
    def is_acknowledged(self) -> bool:
        return self.acknowledged_at is not None
