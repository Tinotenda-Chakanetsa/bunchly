"""Serializers for the onboarding / offboarding module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import (
    ChecklistTaskTemplate,
    ChecklistTemplate,
    OnboardingProgramme,
    OnboardingTask,
)


class ChecklistTaskTemplateSerializer(TenantScopedModelSerializer):
    """A task line within a checklist template."""

    owner_role_display = serializers.CharField(
        source="get_owner_role_display", read_only=True
    )

    class Meta:
        model = ChecklistTaskTemplate
        fields = [
            "id", "template", "title", "description", "owner_role",
            "owner_role_display", "sequence", "due_offset_days", "created_at",
        ]
        read_only_fields = ["created_at"]


class ChecklistTemplateSerializer(TenantScopedModelSerializer):
    """A configurable onboarding / offboarding checklist."""

    programme_type_display = serializers.CharField(
        source="get_programme_type_display", read_only=True
    )
    task_templates = ChecklistTaskTemplateSerializer(many=True, read_only=True)
    task_count = serializers.IntegerField(
        source="task_templates.count", read_only=True
    )

    class Meta:
        model = ChecklistTemplate
        fields = [
            "id", "name", "programme_type", "programme_type_display",
            "description", "is_default", "is_active", "task_templates",
            "task_count", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class OnboardingTaskSerializer(TenantScopedModelSerializer):
    """A task within a running programme."""

    owner_role_display = serializers.CharField(
        source="get_owner_role_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    assigned_to_name = serializers.CharField(
        source="assigned_to.full_name", read_only=True, default=None
    )

    class Meta:
        model = OnboardingTask
        fields = [
            "id", "programme", "title", "description", "owner_role",
            "owner_role_display", "assigned_to", "assigned_to_name",
            "sequence", "status", "status_display", "due_date",
            "completed_at", "completed_by", "notes", "created_at", "updated_at",
        ]
        # Status is owned by the lifecycle actions / service.
        read_only_fields = [
            "programme", "status", "completed_at", "completed_by",
            "created_at", "updated_at",
        ]


class OnboardingProgrammeSerializer(serializers.ModelSerializer):
    """A running programme with its tasks and progress."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    programme_type_display = serializers.CharField(
        source="get_programme_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    template_name = serializers.CharField(
        source="template.name", read_only=True, default=None
    )
    tasks = OnboardingTaskSerializer(many=True, read_only=True)

    class Meta:
        model = OnboardingProgramme
        fields = [
            "id", "employee", "employee_name", "programme_type",
            "programme_type_display", "template", "template_name", "status",
            "status_display", "start_date", "target_completion_date",
            "completed_at", "notes", "tasks", "created_at", "updated_at",
        ]
        read_only_fields = fields


class OnboardingProgrammeListSerializer(serializers.ModelSerializer):
    """Lightweight programme row."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = OnboardingProgramme
        fields = [
            "id", "employee", "employee_name", "programme_type", "status",
            "status_display", "start_date", "target_completion_date",
            "created_at",
        ]


class StartProgrammeSerializer(serializers.Serializer):
    """Input for starting a programme for an employee."""

    employee = serializers.UUIDField()
    programme_type = serializers.ChoiceField(
        choices=["onboarding", "offboarding"], default="onboarding"
    )
    template = serializers.UUIDField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )


class TaskStatusSerializer(serializers.Serializer):
    """Input for changing a task's status."""

    status = serializers.CharField()
    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )
