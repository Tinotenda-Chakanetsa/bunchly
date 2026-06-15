"""Serializers for the data-import module."""
from __future__ import annotations

from rest_framework import serializers

from .enums import ImportEntityType
from .models import ImportBatch, ImportError


class ImportErrorSerializer(serializers.ModelSerializer):
    """One row/field-level error from a validated batch."""

    class Meta:
        model = ImportError
        fields = ["id", "row_number", "field", "error"]
        read_only_fields = fields


class ImportBatchListSerializer(serializers.ModelSerializer):
    """Compact representation for the import-history list."""

    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    entity_type_display = serializers.CharField(
        source="get_entity_type_display", read_only=True
    )

    class Meta:
        model = ImportBatch
        fields = [
            "id", "entity_type", "entity_type_display", "status",
            "status_display", "original_filename", "total_rows", "valid_rows",
            "error_rows", "committed_rows", "committed_at", "created_at",
        ]
        read_only_fields = fields


class ImportBatchSerializer(ImportBatchListSerializer):
    """Detail representation — adds the linked error list."""

    errors = ImportErrorSerializer(many=True, read_only=True)

    class Meta(ImportBatchListSerializer.Meta):
        fields = ImportBatchListSerializer.Meta.fields + ["notes", "errors"]
        read_only_fields = fields


class ValidateUploadSerializer(serializers.Serializer):
    """Multipart input for ``POST /imports/validate/``."""

    entity_type = serializers.ChoiceField(choices=ImportEntityType.choices)
    file = serializers.FileField()


class CommitUploadSerializer(serializers.Serializer):
    """Multipart input for ``POST /imports/{id}/commit/``."""

    file = serializers.FileField()
