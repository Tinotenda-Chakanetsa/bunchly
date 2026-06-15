"""Serializers for tenant administration and settings."""
from __future__ import annotations

from rest_framework import serializers

from .models import (
    Tenant,
    TenantDomain,
    TenantSettings,
    TenantSubscriptionPlan,
    TenantUserMembership,
)


class TenantDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantDomain
        fields = ["id", "domain", "is_primary", "created_at"]


class TenantSubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSubscriptionPlan
        fields = ["id", "code", "name", "max_employees", "max_storage_gb", "is_active"]


class TenantSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSettings
        fields = [
            "id",
            "timezone",
            "locale",
            "primary_color",
            "logo",
            "email_sender_name",
            "email_reply_to",
            "notification_recipients",
            "max_upload_size_mb",
            "allowed_upload_extensions",
            "module_flags",
            "data_retention_days",
            "updated_at",
        ]


class TenantSerializer(serializers.ModelSerializer):
    domains = TenantDomainSerializer(many=True, read_only=True)
    settings = TenantSettingsSerializer(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "slug",
            "legal_name",
            "industry",
            "country",
            "is_active",
            "onboarded_at",
            "domains",
            "settings",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "onboarded_at"]


class TenantCreateSerializer(serializers.ModelSerializer):
    """Platform-admin tenant provisioning. Creates the settings row too."""

    class Meta:
        model = Tenant
        fields = ["id", "name", "legal_name", "industry", "country"]

    def create(self, validated_data):
        tenant = super().create(validated_data)
        TenantSettings.objects.get_or_create(tenant=tenant)
        return tenant


class TenantProvisionSerializer(serializers.Serializer):
    """Input shape for ``POST /tenants/organisations/provision/``.

    Wraps :func:`apps.tenants.services.provision_tenant` so the platform
    admin can create a tenant + its first Organisation Administrator in
    one call. ``admin_password`` is optional — when omitted, the
    response includes a one-time generated password.
    """

    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=50, required=False, allow_blank=True)
    domain = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    legal_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    industry = serializers.CharField(
        max_length=64, required=False, allow_blank=True
    )
    country = serializers.CharField(
        max_length=64, required=False, allow_blank=True
    )
    admin_email = serializers.EmailField()
    admin_first_name = serializers.CharField(
        max_length=120, required=False, allow_blank=True
    )
    admin_last_name = serializers.CharField(
        max_length=120, required=False, allow_blank=True
    )
    admin_password = serializers.CharField(
        min_length=8, required=False, allow_blank=True, write_only=True
    )


class TenantUserMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)

    class Meta:
        model = TenantUserMembership
        fields = [
            "id",
            "tenant",
            "tenant_name",
            "user",
            "user_email",
            "roles",
            "is_owner",
            "is_default",
            "is_active",
            "joined_at",
        ]
        read_only_fields = ["joined_at"]
