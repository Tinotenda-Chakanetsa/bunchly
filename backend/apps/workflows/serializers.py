"""Serializers for the workflow engine."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import Workflow, WorkflowAction, WorkflowInstance, WorkflowStage


class WorkflowStageSerializer(TenantScopedModelSerializer):
    """A configurable approval stage."""

    approver_type_display = serializers.CharField(
        source="get_approver_type_display", read_only=True
    )
    approver_role_name = serializers.CharField(
        source="approver_role.name", read_only=True, default=None
    )
    approver_user_name = serializers.CharField(
        source="approver_user.full_name", read_only=True, default=None
    )

    class Meta:
        model = WorkflowStage
        fields = [
            "id", "workflow", "name", "sequence", "approver_type",
            "approver_type_display", "approver_role", "approver_role_name",
            "approver_user", "approver_user_name", "sla_days",
            "allow_request_info", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        approver_type = attrs.get(
            "approver_type", getattr(self.instance, "approver_type", None)
        )
        role = attrs.get("approver_role", getattr(self.instance, "approver_role", None))
        user = attrs.get("approver_user", getattr(self.instance, "approver_user", None))
        if approver_type == "role" and role is None:
            raise serializers.ValidationError(
                {"approver_role": "A role is required for a role-based stage."}
            )
        if approver_type == "named_user" and user is None:
            raise serializers.ValidationError(
                {"approver_user": "A user is required for a named-user stage."}
            )
        return attrs


class WorkflowSerializer(TenantScopedModelSerializer):
    """A workflow definition with its ordered stages."""

    entity_type_display = serializers.CharField(
        source="get_entity_type_display", read_only=True
    )
    stages = WorkflowStageSerializer(many=True, read_only=True)
    stage_count = serializers.IntegerField(source="stages.count", read_only=True)

    class Meta:
        model = Workflow
        fields = [
            "id", "name", "code", "description", "entity_type",
            "entity_type_display", "is_default", "is_active", "stages",
            "stage_count", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_code(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = Workflow.all_objects.filter(tenant=tenant, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A workflow with this code already exists."
            )
        return value


class WorkflowActionSerializer(serializers.ModelSerializer):
    """An entry in an instance's action log (read-only)."""

    action_display = serializers.CharField(source="get_action_display", read_only=True)
    actor_name = serializers.CharField(
        source="actor.full_name", read_only=True, default=None
    )
    stage_name = serializers.CharField(
        source="stage.name", read_only=True, default=None
    )

    class Meta:
        model = WorkflowAction
        fields = [
            "id", "action", "action_display", "actor", "actor_name",
            "stage", "stage_name", "comment", "created_at",
        ]
        read_only_fields = fields


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    """A running workflow instance with its action history."""

    workflow_name = serializers.CharField(source="workflow.name", read_only=True)
    entity_type_display = serializers.CharField(
        source="workflow.get_entity_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    current_stage_name = serializers.CharField(
        source="current_stage.name", read_only=True, default=None
    )
    subject_employee_name = serializers.CharField(
        source="subject_employee.full_name", read_only=True, default=None
    )
    initiated_by_name = serializers.CharField(
        source="initiated_by.full_name", read_only=True, default=None
    )
    actions = WorkflowActionSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowInstance
        fields = [
            "id", "workflow", "workflow_name", "entity_type_display",
            "entity_id", "subject", "subject_employee",
            "subject_employee_name", "status", "status_display",
            "current_stage", "current_stage_name", "initiated_by",
            "initiated_by_name", "context", "submitted_at", "completed_at",
            "stage_entered_at", "actions", "created_at", "updated_at",
        ]
        read_only_fields = fields


class WorkflowInstanceListSerializer(serializers.ModelSerializer):
    """Lightweight row for instance lists and approval queues."""

    workflow_name = serializers.CharField(source="workflow.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    current_stage_name = serializers.CharField(
        source="current_stage.name", read_only=True, default=None
    )

    class Meta:
        model = WorkflowInstance
        fields = [
            "id", "workflow", "workflow_name", "subject", "status",
            "status_display", "current_stage", "current_stage_name",
            "submitted_at", "created_at",
        ]


class WorkflowInstanceCreateSerializer(serializers.Serializer):
    """Input for opening a workflow instance."""

    workflow = serializers.PrimaryKeyRelatedField(queryset=Workflow.objects.none())
    subject = serializers.CharField(max_length=200)
    entity_type = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default=""
    )
    entity_id = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )
    subject_employee = serializers.PrimaryKeyRelatedField(
        required=False, allow_null=True, queryset=Workflow.objects.none()
    )
    context = serializers.JSONField(required=False, default=dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        if tenant is not None:
            from apps.employees.models import Employee

            self.fields["workflow"].queryset = Workflow.objects.filter(
                tenant=tenant, is_active=True
            )
            self.fields["subject_employee"].queryset = Employee.objects.filter(
                tenant=tenant
            )


class WorkflowDecisionSerializer(serializers.Serializer):
    """Input for an act-on-instance decision."""

    comment = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )
