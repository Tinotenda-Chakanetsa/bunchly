"""DRF permission classes for tenant isolation and RBAC.

Usage on a viewset::

    class EmployeeViewSet(TenantScopedViewSetMixin, ModelViewSet):
        permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
        permission_required = {
            "list": "employees.view_employee",
            "create": "employees.add_employee",
            "default": "employees.view_employee",
        }
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission

SAFE_ACTIONS = {"list", "retrieve", "metadata"}


class IsPlatformAdmin(BasePermission):
    """Only Bunchly platform super administrators."""

    message = "Platform administrator access is required."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_platform_admin", False)
        )


class HasTenant(BasePermission):
    """Request must be bound to a tenant the user belongs to.

    Platform admins are allowed through even without a tenant context
    (they manage tenants rather than tenant data).
    """

    message = "No active organisation context for this request."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(user, "is_platform_admin", False):
            return True
        return getattr(request, "tenant", None) is not None


class HasModulePermission(BasePermission):
    """Checks RBAC permission codenames declared on the view.

    The view declares ``permission_required`` as either a single
    codename string, or a dict mapping DRF actions to codenames with an
    optional ``"default"`` key. Platform admins and tenant owners with
    the wildcard ``*`` permission bypass the check.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(user, "is_platform_admin", False):
            return True

        required = getattr(view, "permission_required", None)
        if not required:
            return True  # no codename declared — IsAuthenticated/HasTenant govern

        codename = self._resolve(required, getattr(view, "action", None), request)
        if codename is None:
            return True

        tenant = getattr(request, "tenant", None)
        return user.has_perm_code(codename, tenant)

    @staticmethod
    def _resolve(required, action, request):
        if isinstance(required, str):
            return required
        if isinstance(required, dict):
            if action and action in required:
                return required[action]
            return required.get("default")
        return None
