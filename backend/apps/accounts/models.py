"""Authentication & RBAC models: User, Permission, Role."""
from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDModel

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Bunchly user — a global identity that may belong to many tenants.

    Tenant membership and roles live on ``tenants.TenantUserMembership``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    # Bunchly platform super administrator — cross-tenant scope.
    is_platform_admin = models.BooleanField(default=False)

    is_email_verified = models.BooleanField(default=False)
    mfa_enabled = models.BooleanField(default=False)

    # Account-lockout tracking (enforced by the login view).
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > timezone.now())

    # --- RBAC -------------------------------------------------------------
    def membership_for(self, tenant):
        """Return the user's active membership for a tenant, or None."""
        if tenant is None:
            return None
        return (
            self.memberships.filter(tenant=tenant, is_active=True)
            .prefetch_related("roles__permissions")
            .first()
        )

    def permission_codes(self, tenant) -> set[str]:
        """All permission codenames the user holds within a tenant."""
        if self.is_platform_admin or self.is_superuser:
            return {"*"}
        membership = self.membership_for(tenant)
        if membership is None:
            return set()
        if membership.is_owner:
            return {"*"}
        codes: set[str] = set()
        for role in membership.roles.all():
            codes.update(role.permissions.values_list("code", flat=True))
        return codes

    def has_perm_code(self, code: str, tenant) -> bool:
        """Check a single RBAC codename within a tenant. Fails closed."""
        if self.is_platform_admin or self.is_superuser:
            return True
        codes = self.permission_codes(tenant)
        return "*" in codes or code in codes


class Permission(UUIDModel, TimeStampedModel):
    """A granular, codename-addressable capability (RBAC catalogue entry)."""

    code = models.CharField(max_length=120, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=60, db_index=True)

    class Meta:
        ordering = ["module", "code"]

    def __str__(self) -> str:
        return self.code


class Role(UUIDModel, TimeStampedModel):
    """A named set of permissions, scoped to a tenant.

    ``tenant`` is null for system templates copied into each tenant on
    provisioning. ``is_system`` roles cannot be deleted by tenant admins.
    """

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="roles",
        null=True,
        blank=True,
        db_index=True,
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"], name="uniq_role_name_per_tenant"
            )
        ]

    def __str__(self) -> str:
        scope = self.tenant.name if self.tenant else "system"
        return f"{self.name} ({scope})"
