"""Serializers for the HR helpdesk / case-management module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import CaseAttachment, CaseCategory, CaseComment, HRCase


class CaseCategorySerializer(TenantScopedModelSerializer):
    """A configurable HR case category."""

    case_count = serializers.IntegerField(source="cases.count", read_only=True)

    class Meta:
        model = CaseCategory
        fields = [
            "id", "name", "code", "description", "default_sla_hours",
            "is_active", "case_count", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_code(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = CaseCategory.all_objects.filter(tenant=tenant, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A case category with this code already exists."
            )
        return value


class CaseCommentSerializer(TenantScopedModelSerializer):
    """A comment on an HR case."""

    author_name = serializers.CharField(
        source="author.full_name", read_only=True, default=None
    )

    class Meta:
        model = CaseComment
        fields = [
            "id", "case", "author", "author_name", "body", "is_internal",
            "created_at",
        ]
        read_only_fields = ["author", "created_at"]


class CaseAttachmentSerializer(TenantScopedModelSerializer):
    """A file attached to an HR case."""

    class Meta:
        model = CaseAttachment
        fields = [
            "id", "case", "file", "description", "uploaded_by", "created_at",
        ]
        read_only_fields = ["uploaded_by", "created_at"]


class HRCaseSerializer(TenantScopedModelSerializer):
    """A full HR case with comments and attachments."""

    reference = serializers.CharField(read_only=True)
    category_name = serializers.CharField(
        source="category.name", read_only=True, default=None
    )
    raised_by_name = serializers.CharField(
        source="raised_by.full_name", read_only=True
    )
    assigned_to_name = serializers.CharField(
        source="assigned_to.full_name", read_only=True, default=None
    )
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    comments = serializers.SerializerMethodField()
    attachments = CaseAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = HRCase
        fields = [
            "id", "reference", "subject", "description", "category",
            "category_name", "raised_by", "raised_by_name", "assigned_to",
            "assigned_to_name", "priority", "priority_display", "status",
            "status_display", "sla_due_at", "resolved_at", "resolution_notes",
            "closed_at", "comments", "attachments", "created_at", "updated_at",
        ]
        # Assignment / status / SLA fields are owned by the service actions.
        read_only_fields = [
            "reference", "raised_by", "assigned_to", "status", "sla_due_at",
            "resolved_at", "resolution_notes", "closed_at",
            "created_at", "updated_at",
        ]

    def get_comments(self, obj):
        """Comments — internal notes are hidden from the case raiser."""
        request = self.context.get("request")
        comments = obj.comments.all()
        user = getattr(request, "user", None)
        raiser_user_id = getattr(obj.raised_by, "user_id", None)
        is_raiser = user is not None and user.id == raiser_user_id
        tenant = getattr(request, "tenant", None)
        can_manage = bool(
            user and user.is_authenticated
            and user.has_perm_code("helpdesk.manage", tenant)
        )
        if is_raiser and not can_manage:
            comments = [c for c in comments if not c.is_internal]
        return CaseCommentSerializer(comments, many=True, context=self.context).data


class HRCaseListSerializer(serializers.ModelSerializer):
    """Lightweight HR case row."""

    category_name = serializers.CharField(
        source="category.name", read_only=True, default=None
    )
    raised_by_name = serializers.CharField(
        source="raised_by.full_name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = HRCase
        fields = [
            "id", "reference", "subject", "category", "category_name",
            "raised_by", "raised_by_name", "priority", "status",
            "status_display", "sla_due_at", "created_at",
        ]


class CaseCreateSerializer(serializers.Serializer):
    """Input for raising an HR case."""

    subject = serializers.CharField(max_length=200)
    description = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    category = serializers.UUIDField(required=False, allow_null=True)
    priority = serializers.ChoiceField(
        choices=["low", "medium", "high", "urgent"], required=False
    )
    employee = serializers.UUIDField(
        required=False,
        help_text="Raise on behalf of an employee (HR only); defaults to self.",
    )


class AssignCaseSerializer(serializers.Serializer):
    """Input for assigning a case to an HR handler."""

    assigned_to = serializers.UUIDField()


class CaseStatusSerializer(serializers.Serializer):
    """Input for an open-status change."""

    status = serializers.ChoiceField(choices=["open", "in_progress", "on_hold"])


class ResolveCaseSerializer(serializers.Serializer):
    """Input for resolving a case."""

    resolution_notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
