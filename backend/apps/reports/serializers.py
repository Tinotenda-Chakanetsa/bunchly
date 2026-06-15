"""Serializers for the reports & analytics module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import SavedReport


class SavedReportSerializer(TenantScopedModelSerializer):
    """A saved report configuration."""

    report_key_display = serializers.CharField(
        source="get_report_key_display", read_only=True
    )
    owner_name = serializers.CharField(
        source="owner.full_name", read_only=True, default=None
    )

    class Meta:
        model = SavedReport
        fields = [
            "id", "name", "report_key", "report_key_display", "description",
            "filters", "owner", "owner_name", "is_shared",
            "created_at", "updated_at",
        ]
        read_only_fields = ["owner", "created_at", "updated_at"]
