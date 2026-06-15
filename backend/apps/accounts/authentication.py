"""Tenant-aware JWT authentication.

Extends SimpleJWT so that, in addition to verifying the token and user,
it resolves the active tenant from the token's ``tenant_id`` claim,
verifies the user is a member of that tenant, and binds the tenant to
the request and request context.
"""
from __future__ import annotations

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from apps.common.context import get_context
from apps.common.db import set_tenant_setting


class TenantJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, token = result
        ctx = get_context()
        ctx.user = user

        tenant = None
        tenant_id = token.get("tenant_id")
        if tenant_id:
            from apps.tenants.models import Tenant

            tenant = Tenant.objects.filter(id=tenant_id, is_active=True).first()
            if tenant is None:
                raise AuthenticationFailed("Organisation is unavailable.")

            # The user must be an active member (platform admins excepted).
            is_member = user.memberships.filter(
                tenant=tenant, is_active=True
            ).exists()
            if not is_member and not user.is_platform_admin:
                raise AuthenticationFailed("No access to this organisation.")

            # Reject a token whose tenant disagrees with the host/header.
            hint = getattr(request, "tenant_hint", None)
            if hint is not None and hint.id != tenant.id:
                raise AuthenticationFailed("Organisation context mismatch.")

        request.tenant = tenant
        ctx.tenant = tenant

        # Activate the Postgres RLS policy for this transaction. Defense
        # in depth: if a viewset forgets to filter by tenant, the policy
        # still scopes every query.
        set_tenant_setting(tenant.id if tenant else None)
        return user, token
