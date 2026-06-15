"""Tenant provisioning service.

One canonical place that knows how to stand up a brand-new tenant + its
first Organisation Administrator. Both the ``provision_tenant``
management command and the ``POST /tenants/organisations/provision/``
endpoint call into here so the two stay in lock-step.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass

from django.core.management import call_command
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import Role, User

from .models import Tenant, TenantDomain, TenantSettings, TenantUserMembership


@dataclass
class ProvisionResult:
    """The artefacts created by :func:`provision_tenant`."""

    tenant: Tenant
    admin: User
    admin_password: str | None  # Only populated when we generated one ourselves.
    tenant_created: bool
    user_created: bool


def provision_tenant(
    *,
    name: str,
    slug: str | None = None,
    domain: str | None = None,
    country: str = "",
    legal_name: str = "",
    industry: str = "",
    admin_email: str,
    admin_first_name: str = "",
    admin_last_name: str = "",
    admin_password: str | None = None,
) -> ProvisionResult:
    """Create (or refresh) a tenant and its first Organisation Administrator.

    Idempotent on ``slug`` + ``admin_email`` — re-running with the same
    inputs touches up the tenant + role permissions and re-binds the
    admin user. If ``admin_password`` is omitted and the user is new, a
    random password is generated and returned on the result.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("Tenant name is required.")

    resolved_slug = (slug or slugify(name)).strip()
    if not resolved_slug:
        raise ValueError("Could not derive a slug from the tenant name.")

    if not admin_email or "@" not in admin_email:
        raise ValueError("A valid admin_email is required.")

    with transaction.atomic():
        # System role templates must exist before we can copy them in.
        if not Role.objects.filter(tenant=None, is_system=True).exists():
            call_command("seed_rbac")

        tenant, tenant_created = Tenant.objects.update_or_create(
            slug=resolved_slug,
            defaults={
                "name": name,
                "legal_name": legal_name or "",
                "industry": industry or "",
                "country": country or "",
                "is_active": True,
                "onboarded_at": timezone.now(),
            },
        )
        TenantSettings.objects.get_or_create(tenant=tenant)

        resolved_domain = (domain or f"{resolved_slug}.bunchly.local").strip().lower()
        TenantDomain.objects.update_or_create(
            domain=resolved_domain,
            defaults={"tenant": tenant, "is_primary": True},
        )

        # Copy every system role into this tenant, refreshing perms too.
        for system_role in Role.objects.filter(tenant=None, is_system=True):
            tenant_role, _ = Role.objects.get_or_create(
                tenant=tenant,
                name=system_role.name,
                defaults={
                    "description": system_role.description,
                    "is_system": True,
                },
            )
            tenant_role.permissions.set(system_role.permissions.all())

        admin_user, user_created = User.objects.get_or_create(
            email=admin_email.strip().lower(),
            defaults={
                "first_name": (admin_first_name or "").strip(),
                "last_name": (admin_last_name or "").strip(),
                "is_active": True,
            },
        )

        generated_password: str | None = None
        if admin_password:
            admin_user.set_password(admin_password)
            admin_user.save(update_fields=["password"])
        elif user_created:
            generated_password = secrets.token_urlsafe(12)
            admin_user.set_password(generated_password)
            admin_user.save(update_fields=["password"])

        admin_role = Role.objects.get(
            tenant=tenant, name="Organisation Administrator"
        )
        membership, _ = TenantUserMembership.objects.get_or_create(
            tenant=tenant,
            user=admin_user,
            defaults={
                "is_owner": True,
                "is_default": True,
                "is_active": True,
            },
        )
        if not membership.is_active or not membership.is_owner:
            membership.is_active = True
            membership.is_owner = True
            membership.save(update_fields=["is_active", "is_owner"])
        membership.roles.set([admin_role])

    return ProvisionResult(
        tenant=tenant,
        admin=admin_user,
        admin_password=generated_password or (admin_password if user_created else None),
        tenant_created=tenant_created,
        user_created=user_created,
    )
