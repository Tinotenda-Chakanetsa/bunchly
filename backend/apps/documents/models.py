"""Document-management models (spec §9.13).

Three tenant-owned models:

``DocumentCategory``  configurable upload categories with per-category
                      rules (required, approval, sensitivity, file limits).
``Document``          a logical document belonging to an employee; carries
                      status, expiry and review metadata.
``DocumentVersion``   an uploaded file revision — version control keeps
                      every upload; the ``is_current`` flag marks the live
                      one.

Upload validation, versioning and the approval flow live in
``services.py``. Uploads / downloads / previews / deletions are recorded
through ``apps.audit`` rather than a bespoke access-log table.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import DocumentStatus


class DocumentCategory(TenantOwnedModel):
    """A configurable category employees may upload documents under.

    Every behaviour a tenant might vary — whether the category is
    compliance-required, needs HR approval, is sensitive, and its file
    constraints — is a field here.
    """

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    description = models.TextField(blank=True)

    is_required = models.BooleanField(
        default=False, help_text="Every employee is expected to hold one."
    )
    requires_approval = models.BooleanField(
        default=False, help_text="Uploads need HR approval before they count."
    )
    is_sensitive = models.BooleanField(
        default=False,
        help_text="Restricted content (medical, banking) — viewable only "
        "by the owner and holders of documents.manage.",
    )
    tracks_expiry = models.BooleanField(
        default=False, help_text="Documents in this category carry an expiry date."
    )
    allowed_extensions = models.JSONField(
        default=list,
        blank=True,
        help_text="Override of permitted file extensions; empty = tenant/"
        "project default.",
    )
    max_file_size_mb = models.PositiveIntegerField(
        default=0, help_text="0 = use the tenant/project default."
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Document categories"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_documentcategory_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Document(TenantOwnedModel):
    """A logical document held against an employee.

    The file content lives on ``DocumentVersion`` rows; this record holds
    the identity, status, expiry and review trail. ``current_version``
    points at the live revision.
    """

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="documents"
    )
    category = models.ForeignKey(
        DocumentCategory, on_delete=models.PROTECT, related_name="documents"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=12,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
        db_index=True,
    )
    is_confidential = models.BooleanField(
        default=False, help_text="Extra restriction on top of the category."
    )

    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)

    current_version = models.ForeignKey(
        "DocumentVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    # Review trail (HR approval).
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "employee", "status"]),
            models.Index(fields=["tenant", "category"]),
            models.Index(fields=["tenant", "status", "expiry_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.employee}"

    @property
    def version_count(self) -> int:
        return self.versions.count()


class DocumentVersion(TenantOwnedModel):
    """One uploaded revision of a document.

    Version control keeps every upload; ``is_current`` marks the live
    file. File metadata is captured at upload so the record is useful
    even if the blob is later moved or purged.
    """

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to="employee-documents/")
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=120, blank=True)
    is_current = models.BooleanField(default=True, db_index=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["document", "-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_number"],
                name="uniq_documentversion_number_per_document",
            )
        ]
        indexes = [models.Index(fields=["tenant", "document", "is_current"])]

    def __str__(self) -> str:
        return f"{self.document.title} v{self.version_number}"
