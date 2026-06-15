"""Notification-engine models (spec §6, §9.15).

Four tenant-owned models:

``NotificationTemplate``  per-tenant, per-event subject/body with an
                          enable/disable toggle and channel choice.
``Notification``          a delivered in-app notification with read state.
``EmailLog``              one row per outbound email — delivery audit and
                          the basis for retry.
``InboundEmail``          stored metadata for received emails (inbound
                          webhook readiness; routing kept deliberately
                          minimal per spec).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import (
    EmailStatus,
    InboundEmailStatus,
    NotificationChannel,
    NotificationLevel,
    NotificationType,
)


class NotificationTemplate(TenantOwnedModel):
    """A configurable template for one notification event in one tenant.

    ``event_key`` ties the template to a ``NotificationType``. Subject and
    body are Django-template strings rendered against a per-event context.
    ``is_enabled`` is the admin's per-notification on/off switch.
    """

    event_key = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        help_text="The event this template renders.",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    channel = models.CharField(
        max_length=10,
        choices=NotificationChannel.choices,
        default=NotificationChannel.BOTH,
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_enabled = models.BooleanField(
        default=True, help_text="Disable to suppress this notification entirely."
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "event_key"],
                name="uniq_notificationtemplate_event_per_tenant",
            )
        ]
        indexes = [models.Index(fields=["tenant", "event_key"])]

    def __str__(self) -> str:
        return f"{self.name} [{self.event_key}]"


class Notification(TenantOwnedModel):
    """An in-app notification delivered to one user."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event_key = models.CharField(
        max_length=50, choices=NotificationType.choices, db_index=True
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    level = models.CharField(
        max_length=10,
        choices=NotificationLevel.choices,
        default=NotificationLevel.INFO,
    )
    url = models.CharField(
        max_length=255, blank=True, help_text="Optional in-app link to the subject."
    )
    # Loose reference to the originating record (no hard FK — cross-module).
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "recipient", "is_read"]),
            models.Index(fields=["tenant", "recipient", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} -> {self.recipient}"


class EmailLog(TenantOwnedModel):
    """One outbound email — delivery audit, retry source, webhook target.

    ``tenant`` is nullable so platform-level mail (e.g. a password reset
    for a user with no organisation yet) can still be logged.
    """

    tenant = models.ForeignKey(  # noqa: DJ001 - intentionally nullable
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        null=True,
        blank=True,
        db_index=True,
    )
    event_key = models.CharField(
        max_length=50, choices=NotificationType.choices, blank=True, db_index=True
    )
    to_email = models.EmailField()
    from_email = models.CharField(max_length=255, blank=True)
    reply_to = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    status = models.CharField(
        max_length=10,
        choices=EmailStatus.choices,
        default=EmailStatus.QUEUED,
        db_index=True,
    )
    provider = models.CharField(max_length=20, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    error_message = models.CharField(max_length=500, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    notification = models.ForeignKey(
        Notification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_logs",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["status", "attempts"]),
        ]

    def __str__(self) -> str:
        return f"{self.to_email} — {self.subject} ({self.status})"


class InboundEmail(TenantOwnedModel):
    """Stored metadata for an inbound email (webhook readiness).

    Per spec, complex routing is intentionally not implemented; the
    record and a best-effort tenant/employee match are enough for a
    future inbound-email-to-case feature to build on.
    """

    tenant = models.ForeignKey(  # noqa: DJ001 - intentionally nullable
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        null=True,
        blank=True,
        db_index=True,
    )
    from_email = models.EmailField()
    to_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    provider = models.CharField(max_length=20, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True, db_index=True)
    received_at = models.DateTimeField(null=True, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=12,
        choices=InboundEmailStatus.choices,
        default=InboundEmailStatus.RECEIVED,
        db_index=True,
    )
    # Best-effort match to a domain record for future case routing.
    matched_entity_type = models.CharField(max_length=80, blank=True)
    matched_entity_id = models.CharField(max_length=64, blank=True)
    processing_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "status"])]

    def __str__(self) -> str:
        return f"Inbound from {self.from_email}: {self.subject}"
