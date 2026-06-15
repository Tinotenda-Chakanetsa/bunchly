"""Viewsets for the policies module (spec §9.24).

Visibility scoping:
- ``policies.manage``  -> manages catalogue, versions, all assignments.
- ``policies.view``    -> reads the catalogue + sees every assignment.
- otherwise            -> sees own assignments only (self-service ack).
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.viewsets import TenantModelViewSet
from apps.employees.models import Employee

from . import services
from .enums import AssignmentStatus
from .models import Policy, PolicyAssignment, PolicyVersion
from .serializers import (
    AcknowledgeSerializer,
    AssignInputSerializer,
    PolicyAssignmentSerializer,
    PolicySerializer,
    PolicyVersionSerializer,
)

_WRITE = {
    "create": "policies.manage",
    "update": "policies.manage",
    "partial_update": "policies.manage",
    "destroy": "policies.manage",
}


def _own_employee(request):
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


def _has(request, code: str) -> bool:
    return request.user.has_perm_code(code, getattr(request, "tenant", None))


class PolicyViewSet(TenantModelViewSet):
    """Policy catalogue. Read-open to every tenant member; writes need manage."""

    queryset = Policy.objects.select_related(
        "owner", "current_version"
    ).prefetch_related("versions")
    serializer_class = PolicySerializer
    permission_required = {**_WRITE}
    search_fields = ["title", "code"]
    filterset_fields = ["category", "is_active"]
    ordering_fields = ["title", "created_at"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE, "policies.policy",
            entity_id=serializer.instance.pk,
            description=f"Created policy {serializer.instance.title}",
        )

    @action(detail=True, methods=["post"], url_path="bulk-assign")
    def bulk_assign(self, request, pk=None):
        """Assign this policy to a list of employees (idempotent per row)."""
        if not _has(request, "policies.manage"):
            raise PermissionDenied("You may not assign policies.")
        policy = self.get_object()
        payload = AssignInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        tenant = getattr(request, "tenant", None)
        employees = list(
            Employee.objects.filter(
                tenant=tenant, pk__in=payload.validated_data["employees"],
            )
        )
        if not employees:
            raise ValidationError({"employees": "No matching employees."})

        services.bulk_assign(
            tenant=tenant, policy=policy, employees=employees,
            due_date=payload.validated_data.get("due_date"),
            assigned_by=request.user,
        )
        record_audit(
            AuditAction.UPDATE, "policies.policy", entity_id=policy.pk,
            description=(
                f"Assigned policy {policy.code} to {len(employees)} "
                f"employee(s)"
            ),
        )
        return Response({"assigned": len(employees)}, status=201)


class PolicyVersionViewSet(TenantModelViewSet):
    """Versioned policy uploads. Writes need ``policies.manage``."""

    queryset = PolicyVersion.objects.select_related("policy", "published_by")
    serializer_class = PolicyVersionSerializer
    permission_required = {**_WRITE}
    filterset_fields = ["policy", "published_at"]
    ordering_fields = ["created_at", "published_at"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.UPLOAD, "policies.version",
            entity_id=serializer.instance.pk,
            description=(
                f"Drafted version {serializer.instance.version} of "
                f"{serializer.instance.policy.title}"
            ),
        )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish this draft version — flips current_version and notifies."""
        if not _has(request, "policies.manage"):
            raise PermissionDenied("You may not publish policy versions.")
        version = self.get_object()
        services.publish_version(version, user=request.user)
        record_audit(
            AuditAction.APPROVE, "policies.version", entity_id=version.pk,
            description=(
                f"Published version {version.version} of "
                f"{version.policy.title}"
            ),
        )
        return Response(
            PolicyVersionSerializer(
                version, context={"request": request}
            ).data
        )


class PolicyAssignmentViewSet(TenantModelViewSet):
    """Policy assignments — every member sees their own; manage sees all."""

    queryset = PolicyAssignment.objects.select_related(
        "policy", "policy__current_version", "employee", "assigned_by",
    )
    serializer_class = PolicyAssignmentSerializer
    permission_required = {
        # Direct create is gated to managers; bulk goes via /policies/{}/bulk-assign/.
        "create": "policies.manage",
        "update": "policies.manage",
        "partial_update": "policies.manage",
        "destroy": "policies.manage",
    }
    filterset_fields = ["policy", "employee"]
    ordering_fields = ["created_at", "due_date", "acknowledged_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if _has(self.request, "policies.manage") or _has(
            self.request, "policies.view"
        ):
            return queryset
        own = _own_employee(self.request)
        return queryset.filter(employee=own) if own else queryset.none()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        # Optional ?status=pending|acknowledged filter, since it's derived.
        status = self.request.query_params.get("status")
        if status == AssignmentStatus.PENDING:
            queryset = queryset.filter(acknowledged_at__isnull=True)
        elif status == AssignmentStatus.ACKNOWLEDGED:
            queryset = queryset.filter(acknowledged_at__isnull=False)
        return queryset

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """Acknowledge this assignment — must be the assigned employee."""
        assignment = self.get_object()
        own = _own_employee(request)
        if own is None or assignment.employee_id != own.id:
            raise PermissionDenied(
                "You may only acknowledge your own policy assignments."
            )
        payload = AcknowledgeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.acknowledge(
            assignment, user=request.user,
            comment=payload.validated_data.get("comment", ""),
        )
        record_audit(
            AuditAction.APPROVE, "policies.assignment", entity_id=assignment.pk,
            description=(
                f"Acknowledged policy {assignment.policy.code} "
                f"({assignment.acknowledged_version.version if assignment.acknowledged_version else ''})"
            ),
        )
        return Response(
            PolicyAssignmentSerializer(
                assignment, context={"request": request}
            ).data
        )

    @action(detail=False, url_path="my-assignments")
    def my_assignments(self, request):
        """The requesting user's own policy assignments."""
        own = _own_employee(request)
        if own is None:
            raise NotFound(
                "You do not have an employee profile in this organisation."
            )
        queryset = self.filter_queryset(
            super().get_queryset().filter(employee=own)
        )
        page = self.paginate_queryset(queryset)
        serializer = PolicyAssignmentSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)
