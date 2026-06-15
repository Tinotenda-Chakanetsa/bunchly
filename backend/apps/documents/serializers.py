"""Serializers for the document-management module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer
from apps.employees.models import Employee

from .models import Document, DocumentCategory, DocumentVersion


class DocumentCategorySerializer(TenantScopedModelSerializer):
    """A configurable document category and its upload rules."""

    document_count = serializers.IntegerField(
        source="documents.count", read_only=True
    )

    class Meta:
        model = DocumentCategory
        fields = [
            "id", "name", "code", "description", "is_required",
            "requires_approval", "is_sensitive", "tracks_expiry",
            "allowed_extensions", "max_file_size_mb", "is_active",
            "document_count", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_code(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = DocumentCategory.all_objects.filter(tenant=tenant, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A document category with this code already exists."
            )
        return value


class DocumentVersionSerializer(serializers.ModelSerializer):
    """A read-only view of one uploaded revision."""

    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = DocumentVersion
        fields = [
            "id", "version_number", "file_url", "original_filename",
            "file_size", "content_type", "is_current", "notes",
            "uploaded_by_name", "created_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj) -> str | None:
        if not obj.file:
            return None
        request = self.context.get("request")
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url


class DocumentSerializer(serializers.ModelSerializer):
    """Full document record with its version history."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_code = serializers.CharField(source="category.code", read_only=True)
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.full_name", read_only=True, default=None
    )
    current_version = DocumentVersionSerializer(read_only=True)
    versions = DocumentVersionSerializer(many=True, read_only=True)
    version_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "employee", "employee_name", "category", "category_name",
            "category_code", "title", "description", "status",
            "status_display", "is_confidential", "issue_date", "expiry_date",
            "current_version", "versions", "version_count", "reviewed_by",
            "reviewed_by_name", "reviewed_at", "review_note",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight row for document lists."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "employee", "employee_name", "category", "category_name",
            "title", "status", "status_display", "is_confidential",
            "expiry_date", "version_count", "created_at",
        ]


class DocumentCreateSerializer(serializers.Serializer):
    """Input for uploading a new document (multipart form)."""

    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    category = serializers.PrimaryKeyRelatedField(
        queryset=DocumentCategory.objects.all()
    )
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    issue_date = serializers.DateField(required=False, allow_null=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    is_confidential = serializers.BooleanField(required=False, default=False)
    file = serializers.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Confine FK choices to the request tenant (prevents cross-tenant IDOR).
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        if tenant is not None:
            self.fields["employee"].queryset = Employee.objects.filter(tenant=tenant)
            self.fields["category"].queryset = DocumentCategory.objects.filter(
                tenant=tenant, is_active=True
            )


class DocumentMetaSerializer(serializers.ModelSerializer):
    """Editable document metadata (the file itself is changed via versions)."""

    class Meta:
        model = Document
        fields = [
            "id", "title", "description", "issue_date", "expiry_date",
            "is_confidential",
        ]


class DocumentVersionUploadSerializer(serializers.Serializer):
    """Input for adding a new version to an existing document."""

    file = serializers.FileField()
    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )


class DocumentReviewSerializer(serializers.Serializer):
    """Input for an HR approve/reject decision."""

    note = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )
