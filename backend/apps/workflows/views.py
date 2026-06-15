"""Viewsets for the workflow engine (spec §10).

- ``WorkflowViewSet`` / ``WorkflowStageViewSet`` — admin configuration of
  workflow definitions and their stages (``workflows.configure``).
- ``WorkflowInstanceViewSet`` — running instances: initiation, the
  generic decision actions and a personal approval queue.

Scoping: ``workflows.view`` holders see every instance; everyone else
sees the instances they initiated, plus their approval queue via the
``my-pending`` action.
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.viewsets import TenantModelViewSet

from . import services
from .enums import WorkflowActionType, WorkflowStatus
from .models import Workflow, WorkflowInstance, WorkflowStage
from .serializers import (
    WorkflowDecisionSerializer,
    WorkflowInstanceCreateSerializer,
    WorkflowInstanceListSerializer,
    WorkflowInstanceSerializer,
    WorkflowSerializer,
    WorkflowStageSerializer,
)

_CONFIGURE = {
    "create": "workflows.configure",
    "update": "workflows.configure",
    "partial_update": "workflows.configure",
    "destroy": "workflows.configure",
}


class WorkflowViewSet(TenantModelViewSet):
    """Workflow definitions. Reading is open; configuring is gated."""

    queryset = Workflow.objects.prefetch_related("stages")
    serializer_class = WorkflowSerializer
    permission_required = _CONFIGURE
    search_fields = ["name", "code"]
    filterset_fields = ["entity_type", "is_active", "is_default"]
    ordering_fields = ["name", "entity_type", "created_at"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE, "workflows.workflow",
            entity_id=serializer.instance.pk,
            description=f"Created workflow {serializer.instance.name}",
        )

    def perform_update(self, serializer):
        serializer.save()
        record_audit(
            AuditAction.UPDATE, "workflows.workflow",
            entity_id=serializer.instance.pk,
            description=f"Updated workflow {serializer.instance.name}",
        )

    def perform_destroy(self, instance):
        pk, name = instance.pk, instance.name
        super().perform_destroy(instance)
        record_audit(
            AuditAction.DELETE, "workflows.workflow", entity_id=pk,
            description=f"Archived workflow {name}",
        )


class WorkflowStageViewSet(TenantModelViewSet):
    """Configurable stages within a workflow."""

    queryset = WorkflowStage.objects.select_related(
        "workflow", "approver_role", "approver_user"
    )
    serializer_class = WorkflowStageSerializer
    permission_required = _CONFIGURE
    filterset_fields = ["workflow", "approver_type"]
    ordering_fields = ["sequence", "created_at"]


class WorkflowInstanceViewSet(TenantModelViewSet):
    """Running workflow instances and their decision actions."""

    queryset = WorkflowInstance.objects.select_related(
        "workflow", "current_stage", "subject_employee", "initiated_by"
    ).prefetch_related("actions", "actions__actor", "actions__stage")
    filterset_fields = ["workflow", "status", "entity_type"]
    search_fields = ["subject", "entity_id"]
    ordering_fields = ["created_at", "submitted_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return WorkflowInstanceCreateSerializer
        if self.action == "list":
            return WorkflowInstanceListSerializer
        return WorkflowInstanceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        tenant = getattr(self.request, "tenant", None)
        if getattr(user, "is_platform_admin", False) or user.has_perm_code(
            "workflows.view", tenant
        ):
            return queryset
        return queryset.filter(initiated_by=user)

    # --- creation ---------------------------------------------------------
    def create(self, request, *args, **kwargs):
        serializer = WorkflowInstanceCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        instance = services.start_instance(
            workflow=data["workflow"],
            subject=data["subject"],
            initiated_by=request.user,
            entity_type=data.get("entity_type", ""),
            entity_id=data.get("entity_id", ""),
            subject_employee=data.get("subject_employee"),
            context=data.get("context") or {},
        )
        record_audit(
            AuditAction.CREATE, "workflows.workflow_instance",
            entity_id=instance.pk,
            description=f"Started workflow '{instance.subject}'",
        )
        return Response(
            WorkflowInstanceSerializer(instance, context={"request": request}).data,
            status=201,
        )

    def perform_destroy(self, instance):
        is_initiator = instance.initiated_by_id == self.request.user.id
        can_configure = self.request.user.has_perm_code(
            "workflows.configure", getattr(self.request, "tenant", None)
        )
        if instance.status != WorkflowStatus.DRAFT or not (
            is_initiator or can_configure
        ):
            raise PermissionDenied(
                "Only a draft workflow can be deleted, by its initiator or an admin."
            )
        pk = instance.pk
        super().perform_destroy(instance)
        record_audit(
            AuditAction.DELETE, "workflows.workflow_instance", entity_id=pk,
            description="Deleted draft workflow instance",
        )

    # --- helpers ----------------------------------------------------------
    def _respond(self, instance):
        return Response(
            WorkflowInstanceSerializer(instance, context={"request": self.request}).data
        )

    def _decision_comment(self, request) -> str:
        payload = WorkflowDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return payload.validated_data.get("comment", "")

    def _require_approver(self, instance):
        if not services.can_user_act(self.request.user, instance):
            raise PermissionDenied(
                "You are not authorised to decide this workflow's current stage."
            )

    def _require_initiator_or_approver(self, instance):
        is_initiator = instance.initiated_by_id == self.request.user.id
        if not is_initiator and not services.can_user_act(self.request.user, instance):
            raise PermissionDenied("You are not a participant in this workflow.")

    # --- lifecycle actions ------------------------------------------------
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit a draft instance into its approval chain."""
        instance = self.get_object()
        if instance.initiated_by_id != request.user.id and not request.user.has_perm_code(
            "workflows.configure", getattr(request, "tenant", None)
        ):
            raise PermissionDenied("Only the initiator may submit this workflow.")
        services.submit_instance(instance, actor=request.user)
        record_audit(
            AuditAction.SUBMIT, "workflows.workflow_instance", entity_id=instance.pk,
            description=f"Submitted workflow '{instance.subject}'",
        )
        return self._respond(instance)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve the instance's current stage."""
        instance = self.get_object()
        self._require_approver(instance)
        services.act(
            instance, action=WorkflowActionType.APPROVE,
            actor=request.user, comment=self._decision_comment(request),
        )
        record_audit(
            AuditAction.APPROVE, "workflows.workflow_instance", entity_id=instance.pk,
            description=f"Approved a stage of '{instance.subject}'",
        )
        return self._respond(instance)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject the instance at its current stage."""
        instance = self.get_object()
        self._require_approver(instance)
        comment = self._decision_comment(request)
        services.act(
            instance, action=WorkflowActionType.REJECT,
            actor=request.user, comment=comment,
        )
        record_audit(
            AuditAction.REJECT, "workflows.workflow_instance", entity_id=instance.pk,
            description=f"Rejected workflow '{instance.subject}'", reason=comment,
        )
        return self._respond(instance)

    @action(detail=True, methods=["post"], url_path="request-info")
    def request_info(self, request, pk=None):
        """Send the instance back to the initiator for more information."""
        instance = self.get_object()
        self._require_approver(instance)
        services.act(
            instance, action=WorkflowActionType.REQUEST_INFO,
            actor=request.user, comment=self._decision_comment(request),
        )
        return self._respond(instance)

    @action(detail=True, methods=["post"], url_path="provide-info")
    def provide_info(self, request, pk=None):
        """Initiator returns the instance to its stage after supplying info."""
        instance = self.get_object()
        if instance.initiated_by_id != request.user.id:
            raise PermissionDenied("Only the initiator may provide information.")
        services.act(
            instance, action=WorkflowActionType.PROVIDE_INFO,
            actor=request.user, comment=self._decision_comment(request),
        )
        return self._respond(instance)

    @action(detail=True, methods=["post"])
    def comment(self, request, pk=None):
        """Add a comment to the instance without changing its state."""
        instance = self.get_object()
        self._require_initiator_or_approver(instance)
        services.act(
            instance, action=WorkflowActionType.COMMENT,
            actor=request.user, comment=self._decision_comment(request),
        )
        return self._respond(instance)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel an open instance."""
        instance = self.get_object()
        is_initiator = instance.initiated_by_id == request.user.id
        if not is_initiator and not request.user.has_perm_code(
            "workflows.configure", getattr(request, "tenant", None)
        ):
            raise PermissionDenied(
                "Only the initiator or an admin may cancel this workflow."
            )
        services.act(
            instance, action=WorkflowActionType.CANCEL,
            actor=request.user, comment=self._decision_comment(request),
        )
        record_audit(
            AuditAction.UPDATE, "workflows.workflow_instance", entity_id=instance.pk,
            description=f"Cancelled workflow '{instance.subject}'",
        )
        return self._respond(instance)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark an approved instance as completed."""
        instance = self.get_object()
        self._require_approver(instance)
        services.act(
            instance, action=WorkflowActionType.COMPLETE,
            actor=request.user, comment=self._decision_comment(request),
        )
        return self._respond(instance)

    @action(detail=False, url_path="my-pending")
    def my_pending(self, request):
        """Open instances awaiting a decision the caller may make."""
        tenant = getattr(request, "tenant", None)
        open_instances = WorkflowInstance.objects.filter(
            tenant=tenant, status=WorkflowStatus.PENDING_APPROVAL
        ).select_related(
            "workflow", "current_stage", "subject_employee", "initiated_by"
        )
        decidable = [
            inst for inst in open_instances
            if services.can_user_act(request.user, inst)
        ]
        page = self.paginate_queryset(decidable)
        serializer = WorkflowInstanceListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
