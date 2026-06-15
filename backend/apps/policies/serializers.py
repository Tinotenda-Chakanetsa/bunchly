"""Serializers for the policies module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import Policy, PolicyAssignment, PolicyVersion


class PolicyVersionSerializer(TenantScopedModelSerializer):
    """A versioned policy document."""

    is_published = serializers.BooleanField(read_only=True)

    class Meta:
        model = PolicyVersion
        fields = [
            "id", "policy", "version", "document", "effective_date",
            "change_summary", "published_at", "published_by",
            "is_published", "created_at", "updated_at",
        ]
        read_only_fields = [
            "published_at", "published_by", "is_published",
            "created_at", "updated_at",
        ]


class PolicySerializer(TenantScopedModelSerializer):
    """A policy catalogue entry with its current version embedded."""

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    owner_name = serializers.CharField(
        source="owner.full_name", read_only=True, default=""
    )
    current_version_detail = PolicyVersionSerializer(
        source="current_version", read_only=True
    )
    assignment_count = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()

    class Meta:
        model = Policy
        fields = [
            "id", "title", "code", "category", "category_display",
            "description", "owner", "owner_name", "requires_acknowledgement",
            "is_active", "current_version", "current_version_detail",
            "assignment_count", "pending_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "current_version", "current_version_detail",
            "assignment_count", "pending_count",
            "created_at", "updated_at",
        ]

    def validate_code(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = Policy.all_objects.filter(tenant=tenant, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A policy with this code already exists."
            )
        return value

    def get_assignment_count(self, obj) -> int:
        return obj.assignments.count()

    def get_pending_count(self, obj) -> int:
        return obj.assignments.filter(acknowledged_at__isnull=True).count()


class PolicyAssignmentSerializer(TenantScopedModelSerializer):
    """A per-employee policy assignment with derived status."""

    policy_title = serializers.CharField(source="policy.title", read_only=True)
    policy_code = serializers.CharField(source="policy.code", read_only=True)
    policy_category = serializers.CharField(
        source="policy.category", read_only=True
    )
    employee_name = serializers.CharField(
        source="employee.full_name", read_only=True
    )
    current_version = serializers.CharField(
        source="policy.current_version.version", read_only=True, default=""
    )
    is_acknowledged = serializers.BooleanField(read_only=True)

    class Meta:
        model = PolicyAssignment
        fields = [
            "id", "policy", "policy_title", "policy_code", "policy_category",
            "employee", "employee_name", "due_date", "acknowledged_at",
            "acknowledged_version", "current_version", "is_acknowledged",
            "comment", "assigned_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "policy_title", "policy_code", "policy_category", "employee_name",
            "current_version", "acknowledged_at", "acknowledged_version",
            "is_acknowledged", "assigned_by", "created_at", "updated_at",
        ]


class AssignInputSerializer(serializers.Serializer):
    """Input for the bulk-assign action."""

    employees = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False
    )
    due_date = serializers.DateField(required=False, allow_null=True)


class AcknowledgeSerializer(serializers.Serializer):
    """Input for the acknowledge action."""

    comment = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )
