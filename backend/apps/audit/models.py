"""Append-only audit trail for sensitive actions."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    VIEW = "view", "View"
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    LOGIN_FAILED = "login_failed", "Login failed"
    PERMISSION_DENIED = "permission_denied", "Permission denied"
    APPROVE = "approve", "Approve"
    REJECT = "reject", "Reject"
    EXPORT = "export", "Export"
    IMPORT = "import", "Import"
    DOWNLOAD = "download", "Download"
    UPLOAD = "upload", "Upload"
    SUBMIT = "submit", "Submit"
    PAYMENT = "payment", "Payment"
    IMPERSONATE_START = "impersonate_start", "Impersonation started"
    IMPERSONATE_END = "impersonate_end", "Impersonation ended"


class AuditLog(models.Model):
    """One immutable record per sensitive action.

    Never store raw secrets/PII here — callers redact salary, bank
    details, national IDs etc. before passing ``changes``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions",
    )

    action = models.CharField(max_length=32, choices=AuditAction.choices, db_index=True)
    entity_type = models.CharField(max_length=120, db_index=True)
    entity_id = models.CharField(max_length=64, blank=True, db_index=True)
    description = models.CharField(max_length=255, blank=True)

    # {"before": {...}, "after": {...}} — redacted by the caller.
    changes = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True)

    request_id = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "entity_type", "entity_id"]),
            models.Index(fields=["tenant", "action"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type}:{self.entity_id}"
