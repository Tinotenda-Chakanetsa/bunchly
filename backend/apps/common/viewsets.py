"""Shared viewset base classes."""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .mixins import SoftDeleteViewSetMixin, TenantScopedViewSetMixin
from .permissions import HasModulePermission, HasTenant


class TenantModelViewSet(
    TenantScopedViewSetMixin, SoftDeleteViewSetMixin, viewsets.ModelViewSet
):
    """Base CRUD viewset for tenant-owned models.

    - filters every queryset to the request tenant,
    - stamps the tenant on create,
    - soft-deletes on destroy,
    - enforces RBAC via ``permission_required`` (declared per subclass).
    """

    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
