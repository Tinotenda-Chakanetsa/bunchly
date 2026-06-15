"""Viewsets for the organisation-structure module.

Reading the structure is open to any tenant member; mutations require
the ``organisation.manage`` permission. Sensitive actions are audited.
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.viewsets import TenantModelViewSet

from .models import (
    CostCentre,
    Department,
    Grade,
    JobTitle,
    Location,
    Position,
    Team,
)
from .serializers import (
    CostCentreSerializer,
    DepartmentSerializer,
    GradeSerializer,
    JobTitleSerializer,
    LocationSerializer,
    PositionSerializer,
    TeamSerializer,
)

# Read actions are ungated (tenant members may view structure); write
# actions require the organisation-management permission.
_WRITE_ONLY = {
    "create": "organisation.manage",
    "update": "organisation.manage",
    "partial_update": "organisation.manage",
    "destroy": "organisation.manage",
}


class _AuditedOrgViewSet(TenantModelViewSet):
    """Adds audit entries for create/update/delete of structural records."""

    permission_required = _WRITE_ONLY
    audit_entity = "organisation.record"

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE,
            self.audit_entity,
            entity_id=serializer.instance.pk,
            description=f"Created {self.audit_entity} {serializer.instance}",
        )

    def perform_update(self, serializer):
        serializer.save()
        record_audit(
            AuditAction.UPDATE,
            self.audit_entity,
            entity_id=serializer.instance.pk,
            description=f"Updated {self.audit_entity} {serializer.instance}",
        )

    def perform_destroy(self, instance):
        pk = instance.pk
        super().perform_destroy(instance)
        record_audit(
            AuditAction.DELETE,
            self.audit_entity,
            entity_id=pk,
            description=f"Archived {self.audit_entity}",
        )


class CostCentreViewSet(_AuditedOrgViewSet):
    queryset = CostCentre.objects.all()
    serializer_class = CostCentreSerializer
    audit_entity = "organisation.cost_centre"
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]
    ordering_fields = ["code", "name", "created_at"]


class LocationViewSet(_AuditedOrgViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    audit_entity = "organisation.location"
    search_fields = ["name", "code", "city", "country"]
    filterset_fields = ["is_active", "country"]
    ordering_fields = ["name", "created_at"]


class GradeViewSet(_AuditedOrgViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    audit_entity = "organisation.grade"
    search_fields = ["name", "code"]
    filterset_fields = ["is_active", "level"]
    ordering_fields = ["level", "code", "created_at"]


class JobTitleViewSet(_AuditedOrgViewSet):
    queryset = JobTitle.objects.all()
    serializer_class = JobTitleSerializer
    audit_entity = "organisation.job_title"
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]


class TeamViewSet(_AuditedOrgViewSet):
    queryset = Team.objects.select_related("department")
    serializer_class = TeamSerializer
    audit_entity = "organisation.team"
    search_fields = ["name", "code"]
    filterset_fields = ["is_active", "department"]
    ordering_fields = ["name", "created_at"]


class DepartmentViewSet(_AuditedOrgViewSet):
    queryset = Department.objects.select_related("parent", "cost_centre", "location")
    serializer_class = DepartmentSerializer
    audit_entity = "organisation.department"
    search_fields = ["name", "code"]
    filterset_fields = ["is_active", "parent", "cost_centre"]
    ordering_fields = ["name", "created_at"]

    @action(detail=False, methods=["get"])
    def chart(self, request):
        """Nested department tree for the organisation chart."""
        departments = list(self.get_queryset())
        by_parent: dict[str | None, list] = {}
        for dept in departments:
            by_parent.setdefault(str(dept.parent_id) if dept.parent_id else None, []).append(dept)

        def build(parent_id):
            return [
                {
                    "id": str(d.id),
                    "name": d.name,
                    "code": d.code,
                    "is_active": d.is_active,
                    "children": build(str(d.id)),
                }
                for d in by_parent.get(parent_id, [])
            ]

        return Response({"tree": build(None)})


class PositionViewSet(_AuditedOrgViewSet):
    queryset = Position.objects.select_related(
        "job_title", "department", "grade", "location", "reports_to"
    )
    serializer_class = PositionSerializer
    audit_entity = "organisation.position"
    search_fields = ["name", "job_title__name", "department__name"]
    filterset_fields = ["is_active", "is_vacant", "department", "grade", "location"]
    ordering_fields = ["created_at"]

    @action(detail=False, methods=["get"])
    def vacant(self, request):
        """Vacant positions — supports headcount-planning reports."""
        page = self.paginate_queryset(self.get_queryset().filter(is_vacant=True))
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
