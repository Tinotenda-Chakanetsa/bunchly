"""Viewset / serializer mixins for tenant-scoped data access."""
from __future__ import annotations


class TenantScopedViewSetMixin:
    """Filters every queryset by the request tenant and stamps it on create.

    Guarantees no endpoint can return another tenant's rows (prevents
    IDOR) — the filter is applied in ``get_queryset`` regardless of the
    object id supplied in the URL.
    """

    def get_tenant(self):
        return getattr(self.request, "tenant", None)

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant = self.get_tenant()
        if tenant is None:
            # Spec §8.A: a platform admin "Cannot casually access tenant
            # HR data unless explicitly elevated and audited". Without a
            # bound tenant context (i.e. they haven't impersonated a
            # specific tenant) we return empty, never a cross-tenant
            # mash-up. Impersonation issues a fresh JWT with the target
            # tenant_id claim, which TenantJWTAuthentication binds to
            # request.tenant — at which point this filter kicks in
            # exactly like any other tenant member's request.
            return queryset.none()
        return queryset.filter(tenant=tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.get_tenant())


class SoftDeleteViewSetMixin:
    """Performs soft deletes through the model's ``delete()`` override."""

    def perform_destroy(self, instance) -> None:
        instance.delete()
