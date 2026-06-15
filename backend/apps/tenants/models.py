"""Multi-tenancy core models.

Bunchly uses a shared-database, ``tenant_id``-column isolation strategy.
``Tenant`` is the organisation; every tenant-owned domain model carries a
FK to it (see ``apps.common.models.TenantOwnedModel``).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import SoftDeleteModel, TimeStampedModel, UUIDModel


class Tenant(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """An organisation using Bunchly. The root of every isolation boundary."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=80, unique=True, db_index=True)
    legal_name = models.CharField(max_length=255, blank=True)
    industry = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    onboarded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active", "slug"])]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:80]
        super().save(*args, **kwargs)


class TenantDomain(UUIDModel, TimeStampedModel):
    """A subdomain or custom domain that resolves to a tenant."""

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="domains"
    )
    domain = models.CharField(max_length=255, unique=True, db_index=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "domain"]

    def __str__(self) -> str:
        return self.domain


class TenantSubscriptionPlan(UUIDModel, TimeStampedModel):
    """Billing plan placeholder — supports future monetisation."""

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    max_employees = models.PositiveIntegerField(default=0)  # 0 = unlimited
    max_storage_gb = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class TenantSettings(UUIDModel, TimeStampedModel):
    """Per-tenant configuration. One row per tenant.

    Email sender identity, notification recipients and module toggles are
    stored here so nothing organisation-specific is hard-coded.
    """

    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE, related_name="settings"
    )
    plan = models.ForeignKey(
        TenantSubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenants",
    )
    timezone = models.CharField(max_length=64, default="UTC")
    locale = models.CharField(max_length=16, default="en-us")
    primary_color = models.CharField(max_length=9, default="#2563eb")
    logo = models.FileField(upload_to="tenant-logos/", null=True, blank=True)

    # Email identity (overrides project defaults; never hard-coded).
    email_sender_name = models.CharField(max_length=120, blank=True)
    email_reply_to = models.EmailField(blank=True)

    # Notification routing — admin-configurable recipients per event type,
    # e.g. {"leave_finance_notice": ["finance@org.example"]}.
    notification_recipients = models.JSONField(default=dict, blank=True)

    # Upload controls (fall back to project defaults when 0/empty).
    max_upload_size_mb = models.PositiveIntegerField(default=0)
    allowed_upload_extensions = models.JSONField(default=list, blank=True)

    # Module enable/disable toggles, e.g. {"payroll": false}.
    module_flags = models.JSONField(default=dict, blank=True)

    # Data retention period in days (0 = retain indefinitely).
    data_retention_days = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"Settings for {self.tenant.name}"


class TenantUserMembership(UUIDModel, TimeStampedModel):
    """Links a user to a tenant and the roles they hold within it.

    A user may belong to multiple tenants; the JWT carries the active
    tenant for a session.
    """

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    roles = models.ManyToManyField(
        "accounts.Role", related_name="memberships", blank=True
    )
    # Tenant owner: full access within the tenant (wildcard permission).
    is_owner = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    invited_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user"], name="uniq_tenant_user_membership"
            )
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["tenant", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.tenant}"
