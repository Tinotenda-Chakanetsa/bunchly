"""Viewsets for the asset-management module (spec §9.23).

Assets and categories are managed by ``assets.manage`` holders and
browsable by any ``assets.view`` holder. Asset assignments are scoped:
``assets.manage`` sees every assignment, everyone else sees only their
own (the basis for an employee's asset-return checklist).
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
from .models import Asset, AssetAssignment, AssetCategory
from .serializers import (
    AssetAssignmentSerializer,
    AssetCategorySerializer,
    AssetSerializer,
    AssignAssetSerializer,
    ReportLostSerializer,
    ReturnAssetSerializer,
)

_WRITE = {
    "create": "assets.manage",
    "update": "assets.manage",
    "partial_update": "assets.manage",
    "destroy": "assets.manage",
}


def _own_employee(request) -> Employee | None:
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


def _can_manage(request) -> bool:
    return request.user.has_perm_code(
        "assets.manage", getattr(request, "tenant", None)
    )


class AssetCategoryViewSet(TenantModelViewSet):
    """Configurable asset categories."""

    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    permission_required = {"default": "assets.view", **_WRITE}
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]


class AssetViewSet(TenantModelViewSet):
    """The company asset register."""

    queryset = Asset.objects.select_related("category")
    serializer_class = AssetSerializer
    permission_required = {
        "default": "assets.view",
        "assign": "assets.manage",
        **_WRITE,
    }
    search_fields = ["name", "asset_tag", "serial_number"]
    filterset_fields = ["category", "status", "condition"]
    ordering_fields = ["name", "created_at"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE, "assets.asset", entity_id=serializer.instance.pk,
            description=f"Registered asset {serializer.instance.asset_tag}",
        )

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Issue this asset to an employee."""
        asset = self.get_object()
        payload = AssignAssetSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        tenant = getattr(request, "tenant", None)
        employee = Employee.objects.filter(
            tenant=tenant, pk=payload.validated_data["employee"]
        ).first()
        if employee is None:
            raise ValidationError({"employee": "Employee not found."})

        assignment = services.assign_asset(
            tenant=tenant,
            asset=asset,
            employee=employee,
            issued_by=request.user,
            issued_date=payload.validated_data.get("issued_date"),
            due_return_date=payload.validated_data.get("due_return_date"),
            issue_condition=payload.validated_data.get("issue_condition", ""),
            notes=payload.validated_data.get("notes", ""),
        )
        record_audit(
            AuditAction.UPDATE, "assets.asset", entity_id=asset.pk,
            description=f"Assigned asset {asset.asset_tag} to {employee}",
        )
        return Response(
            AssetAssignmentSerializer(
                assignment, context={"request": request}
            ).data,
            status=201,
        )


class AssetAssignmentViewSet(TenantModelViewSet):
    """Asset assignments and their return lifecycle."""

    queryset = AssetAssignment.objects.select_related(
        "asset", "asset__category", "employee", "issued_by", "returned_to"
    )
    serializer_class = AssetAssignmentSerializer
    permission_required = {
        "create": "assets.manage",
        "update": "assets.manage",
        "partial_update": "assets.manage",
        "destroy": "assets.manage",
        "return_asset": "assets.manage",
        "report_lost": "assets.manage",
    }
    filterset_fields = ["asset", "employee", "status"]
    ordering_fields = ["issued_date", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if _can_manage(self.request):
            return queryset
        own = _own_employee(self.request)
        return queryset.filter(employee=own) if own else queryset.none()

    @action(detail=True, methods=["post"], url_path="return")
    def return_asset(self, request, pk=None):
        """Record the return of an issued asset."""
        assignment = self.get_object()
        payload = ReturnAssetSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.return_asset(
            assignment,
            returned_to=request.user,
            return_condition=payload.validated_data.get("return_condition", ""),
            returned_date=payload.validated_data.get("returned_date"),
            notes=payload.validated_data.get("notes", ""),
        )
        record_audit(
            AuditAction.UPDATE, "assets.asset", entity_id=assignment.asset_id,
            description=f"Returned asset {assignment.asset.asset_tag}",
        )
        return Response(
            AssetAssignmentSerializer(
                assignment, context={"request": request}
            ).data
        )

    @action(detail=True, methods=["post"], url_path="report-lost")
    def report_lost(self, request, pk=None):
        """Report an issued asset as lost."""
        assignment = self.get_object()
        payload = ReportLostSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.report_lost(
            assignment, notes=payload.validated_data.get("notes", "")
        )
        record_audit(
            AuditAction.UPDATE, "assets.asset", entity_id=assignment.asset_id,
            description=f"Reported asset {assignment.asset.asset_tag} lost",
        )
        return Response(
            AssetAssignmentSerializer(
                assignment, context={"request": request}
            ).data
        )

    @action(detail=False, url_path="my-assets")
    def my_assets(self, request):
        """Assets currently issued to the requesting user."""
        own = _own_employee(request)
        if own is None:
            raise NotFound("You do not have an employee profile in this organisation.")
        queryset = self.filter_queryset(
            self.get_queryset().filter(employee=own)
        )
        page = self.paginate_queryset(queryset)
        serializer = AssetAssignmentSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, url_path="pending-returns")
    def pending_returns(self, request):
        """Still-issued assets for an employee — the return checklist.

        ``?employee=<id>`` targets a specific employee (needs
        ``assets.manage``); otherwise the requesting user's own.
        """
        employee_id = request.query_params.get("employee")
        if employee_id:
            if not _can_manage(request):
                raise PermissionDenied(
                    "You may only view your own pending returns."
                )
            employee = Employee.objects.filter(
                tenant=getattr(request, "tenant", None), pk=employee_id
            ).first()
        else:
            employee = _own_employee(request)
        if employee is None:
            raise NotFound("Employee not found.")
        assignments = services.pending_returns(employee)
        serializer = AssetAssignmentSerializer(
            assignments, many=True, context={"request": request}
        )
        return Response({"employee": str(employee.pk), "results": serializer.data})
