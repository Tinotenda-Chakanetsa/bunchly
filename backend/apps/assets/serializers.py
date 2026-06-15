"""Serializers for the asset-management module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import Asset, AssetAssignment, AssetCategory


class AssetCategorySerializer(TenantScopedModelSerializer):
    """A configurable asset category."""

    asset_count = serializers.IntegerField(source="assets.count", read_only=True)

    class Meta:
        model = AssetCategory
        fields = [
            "id", "name", "code", "description", "is_active", "asset_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_code(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = AssetCategory.all_objects.filter(tenant=tenant, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "An asset category with this code already exists."
            )
        return value


class AssetSerializer(TenantScopedModelSerializer):
    """A tracked company asset."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    condition_display = serializers.CharField(
        source="get_condition_display", read_only=True
    )

    class Meta:
        model = Asset
        fields = [
            "id", "category", "category_name", "name", "asset_tag",
            "serial_number", "description", "status", "status_display",
            "condition", "condition_display", "purchase_date",
            "purchase_cost", "currency", "location", "notes",
            "created_at", "updated_at",
        ]
        # Status is moved by the assign / return / lost service actions.
        read_only_fields = ["status", "created_at", "updated_at"]

    def validate_asset_tag(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = Asset.all_objects.filter(tenant=tenant, asset_tag=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "An asset with this tag already exists."
            )
        return value


class AssetAssignmentSerializer(TenantScopedModelSerializer):
    """An asset issued to an employee."""

    asset_name = serializers.CharField(source="asset.name", read_only=True)
    asset_tag = serializers.CharField(source="asset.asset_tag", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = AssetAssignment
        fields = [
            "id", "asset", "asset_name", "asset_tag", "employee",
            "employee_name", "status", "status_display", "issued_date",
            "issued_by", "issue_condition", "due_return_date",
            "returned_date", "return_condition", "returned_to", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class AssignAssetSerializer(serializers.Serializer):
    """Input for issuing an asset to an employee."""

    employee = serializers.UUIDField()
    issued_date = serializers.DateField(required=False, allow_null=True)
    due_return_date = serializers.DateField(required=False, allow_null=True)
    issue_condition = serializers.CharField(
        required=False, allow_blank=True, max_length=10, default=""
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )


class ReturnAssetSerializer(serializers.Serializer):
    """Input for recording an asset return."""

    return_condition = serializers.CharField(
        required=False, allow_blank=True, max_length=10, default=""
    )
    returned_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )


class ReportLostSerializer(serializers.Serializer):
    """Input for reporting an assigned asset lost."""

    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )
