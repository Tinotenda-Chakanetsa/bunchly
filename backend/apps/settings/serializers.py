"""Serializers for the system-settings module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from . import services
from .models import SystemSetting


class SystemSettingSerializer(TenantScopedModelSerializer):
    """A single typed configuration value, with its cast representation."""

    value_type_display = serializers.CharField(
        source="get_value_type_display", read_only=True
    )
    typed_value = serializers.SerializerMethodField()

    class Meta:
        model = SystemSetting
        fields = [
            "id", "key", "group", "label", "description", "value_type",
            "value_type_display", "value", "typed_value", "is_public",
            "is_editable", "created_at", "updated_at",
        ]
        read_only_fields = ["is_editable", "created_at", "updated_at"]

    def get_typed_value(self, obj):
        """The value cast to its declared Python type."""
        try:
            return services.cast_value(obj.value, obj.value_type)
        except Exception:  # pragma: no cover - defensive
            return obj.value

    def validate_key(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = SystemSetting.all_objects.filter(tenant=tenant, key=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A setting with this key already exists."
            )
        return value

    def validate(self, attrs):
        value_type = attrs.get(
            "value_type", getattr(self.instance, "value_type", None)
        )
        if "value" in attrs and value_type:
            services.validate_value(attrs["value"], value_type)
        return attrs
