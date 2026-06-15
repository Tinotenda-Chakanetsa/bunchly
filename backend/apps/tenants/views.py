"""Tenant administration & settings APIs."""
from __future__ import annotations

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import HasTenant, IsPlatformAdmin

from apps.accounts.tokens import tokens_for_user
from apps.audit.models import AuditAction
from apps.audit.services import record_audit

from . import services
from .models import Tenant, TenantSettings
from .serializers import (
    TenantCreateSerializer,
    TenantProvisionSerializer,
    TenantSerializer,
    TenantSettingsSerializer,
)


class TenantViewSet(viewsets.ModelViewSet):
    """Platform-admin management of organisations (tenants)."""

    queryset = Tenant.objects.all().prefetch_related("domains").select_related(
        "settings"
    )
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    search_fields = ["name", "slug", "legal_name"]
    ordering_fields = ["name", "created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return TenantCreateSerializer
        return TenantSerializer

    def perform_create(self, serializer):
        serializer.save(onboarded_at=timezone.now())

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        tenant = self.get_object()
        tenant.is_active = False
        tenant.save(update_fields=["is_active", "updated_at"])
        return Response({"status": "deactivated"})

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        tenant = self.get_object()
        tenant.is_active = True
        tenant.save(update_fields=["is_active", "updated_at"])
        return Response({"status": "activated"})

    @action(detail=True, methods=["post"])
    def impersonate(self, request, pk=None):
        """Enter a tenant as a platform admin — audited + explicit.

        Issues a fresh JWT bound to the target tenant with an
        ``impersonating: true`` claim. The frontend uses that claim to
        render a persistent banner and to expose an Exit-impersonation
        action. Every start is logged to the audit trail so the
        impersonated tenant's owner can see who entered, when, and from
        where.
        """
        tenant = self.get_object()
        if not tenant.is_active:
            raise ValidationError({"detail": "Tenant is deactivated."})

        record_audit(
            AuditAction.IMPERSONATE_START,
            "tenant",
            entity_id=tenant.pk,
            description=(
                f"Platform admin {request.user.email} entered tenant "
                f"{tenant.slug}"
            ),
            tenant=tenant,
            actor=request.user,
        )
        tokens = tokens_for_user(
            request.user, tenant=tenant, impersonating=True
        )
        return Response(
            {
                **tokens,
                "active_tenant_id": str(tenant.id),
                "tenant_slug": tenant.slug,
                "tenant_name": tenant.name,
                "impersonating": True,
            }
        )

    @action(detail=False, methods=["post"])
    def provision(self, request):
        """One-shot tenant provisioning: tenant + roles + first admin user.

        Mirrors ``python manage.py provision_tenant`` so platform admins
        don't have to drop to a shell to stand up a new organisation.
        Idempotent on ``slug`` + ``admin_email``.
        """
        payload = TenantProvisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        try:
            result = services.provision_tenant(
                name=data["name"],
                slug=data.get("slug") or None,
                domain=data.get("domain") or None,
                country=data.get("country") or "",
                legal_name=data.get("legal_name") or "",
                industry=data.get("industry") or "",
                admin_email=data["admin_email"],
                admin_first_name=data.get("admin_first_name") or "",
                admin_last_name=data.get("admin_last_name") or "",
                admin_password=data.get("admin_password") or None,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)})

        return Response(
            {
                "tenant": TenantSerializer(result.tenant).data,
                "admin": {
                    "id": str(result.admin.id),
                    "email": result.admin.email,
                    "created": result.user_created,
                },
                # Only populated when we generated a password ourselves —
                # the client must show this once and never store it.
                "one_time_password": result.admin_password,
                "tenant_created": result.tenant_created,
            },
            status=status.HTTP_201_CREATED if result.tenant_created else status.HTTP_200_OK,
        )


class CurrentTenantViewSet(viewsets.ViewSet):
    """The authenticated user's active organisation and its settings."""

    permission_classes = [IsAuthenticated, HasTenant]

    def list(self, request):
        tenant = request.tenant
        if tenant is None:
            raise NotFound("No active organisation for this session.")
        return Response(TenantSerializer(tenant).data)

    @action(detail=False, methods=["get", "patch"], url_path="settings")
    def settings(self, request):
        tenant = request.tenant
        if tenant is None:
            raise NotFound("No active organisation for this session.")
        obj, _ = TenantSettings.objects.get_or_create(tenant=tenant)

        if request.method == "GET":
            return Response(TenantSettingsSerializer(obj).data)

        # Mutation requires the settings-management permission.
        if not request.user.has_perm_code("tenant.manage_settings", tenant):
            raise PermissionDenied("You cannot change organisation settings.")
        serializer = TenantSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
