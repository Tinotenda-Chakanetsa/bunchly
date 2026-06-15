"""JWT issuance helpers — embeds the active tenant as a token claim."""
from __future__ import annotations

from rest_framework_simplejwt.tokens import RefreshToken


def tokens_for_user(user, tenant=None, *, impersonating: bool = False) -> dict[str, str]:
    """Issue an access/refresh token pair, optionally bound to a tenant.

    Custom claims set on the refresh token are copied onto the access
    token by SimpleJWT, so the tenant context travels with every request.

    ``impersonating`` is set when a platform admin has explicitly entered
    a tenant via the audited impersonation flow. The frontend uses the
    flag to render a "you are viewing as Bunchly support" banner.
    """
    refresh = RefreshToken.for_user(user)
    refresh["email"] = user.email
    refresh["is_platform_admin"] = user.is_platform_admin
    if tenant is not None:
        refresh["tenant_id"] = str(tenant.id)
        refresh["tenant_slug"] = tenant.slug
    if impersonating:
        refresh["impersonating"] = True

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }
