"""Read-only audit-log API — tenant-scoped, permission-gated."""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.common.permissions import HasModulePermission, HasTenant

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Audit trail. Read-only by design — entries are immutable."""

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "audit.view"
    filterset_fields = ["action", "entity_type", "actor"]
    search_fields = ["entity_type", "entity_id", "description"]
    ordering_fields = ["created_at", "action"]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        return (
            AuditLog.objects.filter(tenant=tenant)
            .select_related("actor")
            .order_by("-created_at")
        )
