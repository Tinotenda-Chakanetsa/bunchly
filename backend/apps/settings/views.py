"""Viewset for the system-settings module.

Public settings are readable by any tenant member; non-public settings
and all writes require ``tenant.manage_settings``.
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.viewsets import TenantModelViewSet

from . import services
from .models import SystemSetting
from .serializers import SystemSettingSerializer


class SystemSettingViewSet(TenantModelViewSet):
    """Per-tenant operational settings."""

    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_required = {
        "create": "tenant.manage_settings",
        "update": "tenant.manage_settings",
        "partial_update": "tenant.manage_settings",
        "destroy": "tenant.manage_settings",
        "seed_defaults": "tenant.manage_settings",
    }
    search_fields = ["key", "label"]
    filterset_fields = ["group", "value_type", "is_public"]
    ordering_fields = ["group", "key"]

    def _can_manage(self) -> bool:
        return self.request.user.has_perm_code(
            "tenant.manage_settings", getattr(self.request, "tenant", None)
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        # Non-admins only ever see settings flagged public.
        if not self._can_manage():
            return queryset.filter(is_public=True)
        return queryset

    def perform_update(self, serializer):
        if not serializer.instance.is_editable:
            raise ValidationError(
                f"Setting '{serializer.instance.key}' is locked and "
                f"cannot be changed."
            )
        serializer.save()
        record_audit(
            AuditAction.UPDATE, "settings.system_setting",
            entity_id=serializer.instance.pk,
            description=f"Updated setting {serializer.instance.key}",
        )

    @action(detail=False, methods=["post"], url_path="seed-defaults")
    def seed_defaults(self, request):
        """Create any missing catalogue settings for the tenant."""
        created = services.seed_defaults(getattr(request, "tenant", None))
        return Response({"created": created})

    @action(detail=False)
    def public(self, request):
        """The tenant's public (client-readable) settings as a key map."""
        settings = SystemSetting.objects.filter(
            tenant=getattr(request, "tenant", None), is_public=True
        )
        return Response({
            s.key: services.cast_value(s.value, s.value_type) for s in settings
        })
