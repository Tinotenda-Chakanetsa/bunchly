"""Serializers for authentication, users, roles and permissions."""
from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.tenants.models import TenantUserMembership

from .models import Permission, Role, User


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code", "name", "module"]


class RoleSerializer(serializers.ModelSerializer):
    permission_codes = serializers.SlugRelatedField(
        source="permissions",
        slug_field="code",
        queryset=Permission.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "is_system",
            "permission_codes",
            "created_at",
        ]
        read_only_fields = ["is_system"]


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "avatar",
            "is_active",
            "is_platform_admin",
            "is_email_verified",
            "mfa_enabled",
            "created_at",
        ]
        read_only_fields = ["is_platform_admin", "is_email_verified", "created_at"]


class MembershipBriefSerializer(serializers.ModelSerializer):
    tenant_id = serializers.UUIDField(source="tenant.id", read_only=True)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    tenant_slug = serializers.CharField(source="tenant.slug", read_only=True)
    role_names = serializers.SlugRelatedField(
        source="roles", slug_field="name", many=True, read_only=True
    )

    class Meta:
        model = TenantUserMembership
        fields = [
            "id",
            "tenant_id",
            "tenant_name",
            "tenant_slug",
            "is_owner",
            "is_default",
            "role_names",
        ]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    # Optional: pick a specific organisation when the user has several.
    tenant_slug = serializers.SlugField(required=False, allow_blank=True)


class MeSerializer(serializers.Serializer):
    """Current-user payload: profile, memberships and active permissions."""

    user = UserSerializer()
    memberships = MembershipBriefSerializer(many=True)
    active_tenant_id = serializers.UUIDField(allow_null=True)
    permissions = serializers.ListField(child=serializers.CharField())


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class InviteUserSerializer(serializers.Serializer):
    """Invite a user into the current tenant, assigning roles."""

    email = serializers.EmailField()
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    role_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    is_owner = serializers.BooleanField(default=False)
