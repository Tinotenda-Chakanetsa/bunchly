"""HR helpdesk / case-management models (spec §9.22).

``CaseCategory``    configurable case types, each with an SLA target.
``HRCase``          an employee-raised request with priority, assignee,
                    SLA tracking and a status lifecycle.
``CaseComment``     a threaded comment; internal notes are HR-only.
``CaseAttachment``  a file attached to a case.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import CasePriority, CaseStatus


class CaseCategory(TenantOwnedModel):
    """A configurable HR case category (spec §9.22 default categories)."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    description = models.CharField(max_length=255, blank=True)
    default_sla_hours = models.PositiveIntegerField(
        default=0, help_text="Target resolution time in hours; 0 = no SLA.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Case categories"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_casecategory_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return self.name


class HRCase(TenantOwnedModel):
    """An HR request / ticket raised by an employee (spec §9.22)."""

    reference = models.CharField(max_length=40, db_index=True)
    subject = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        CaseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases",
    )
    raised_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="hr_cases",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_hr_cases",
    )
    priority = models.CharField(
        max_length=10, choices=CasePriority.choices, default=CasePriority.MEDIUM
    )
    status = models.CharField(
        max_length=12,
        choices=CaseStatus.choices,
        default=CaseStatus.OPEN,
        db_index=True,
    )
    sla_due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    # Optional link when the case originated from an inbound email.
    source_inbound_email = models.ForeignKey(
        "notifications.InboundEmail",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hr_cases",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "raised_by", "status"]),
            models.Index(fields=["tenant", "assigned_to", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.subject}"


class CaseComment(TenantOwnedModel):
    """A comment on an HR case; internal notes are hidden from the raiser."""

    case = models.ForeignKey(
        HRCase, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    body = models.TextField()
    is_internal = models.BooleanField(
        default=False, help_text="An HR-only note, not shown to the employee."
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["tenant", "case", "created_at"])]

    def __str__(self) -> str:
        return f"Comment on {self.case.reference}"


class CaseAttachment(TenantOwnedModel):
    """A file attached to an HR case."""

    case = models.ForeignKey(
        HRCase, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="hr-case-attachments/")
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "case"])]

    def __str__(self) -> str:
        return f"Attachment on {self.case.reference}"
