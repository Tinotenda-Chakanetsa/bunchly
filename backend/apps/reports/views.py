"""Views for the reports & analytics module (spec §9.16, §9.17).

- ``ReportCatalogueView``  the list of available reports.
- ``ReportRunView``        run a report and return JSON.
- ``ReportExportView``     run a report and return a CSV / XLSX download.
- ``DashboardView``        role-based dashboard metrics.
- ``SavedReportViewSet``   CRUD over saved report configurations.

The module is read-only over the rest of the system; every report and
dashboard query is tenant-scoped.
"""
from __future__ import annotations

from datetime import date

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.permissions import HasModulePermission, HasTenant
from apps.common.viewsets import TenantModelViewSet
from apps.employees.models import Employee

from . import dashboards
from .enums import DashboardAudience
from .models import SavedReport
from .registry import report_catalogue, run_report
from .exporters import export_report
from .serializers import SavedReportSerializer


def _parse_date(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError({field: f"Invalid date '{value}' — use YYYY-MM-DD."})


def _parse_filters(query_params) -> dict:
    """Build the report filter dict from request query parameters."""
    filters: dict = {
        "date_from": _parse_date(query_params.get("date_from"), "date_from"),
        "date_to": _parse_date(query_params.get("date_to"), "date_to"),
        "department": query_params.get("department") or None,
    }
    year = query_params.get("year")
    if year:
        try:
            filters["year"] = int(year)
        except ValueError:
            raise ValidationError({"year": "Year must be a number."})
    return filters


def _own_employee(request) -> Employee | None:
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


class ReportCatalogueView(APIView):
    """List the reports available to run / export."""

    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "reports.view"

    def get(self, request):
        return Response({"reports": report_catalogue()})


class ReportRunView(APIView):
    """Run a report and return its columns / rows / summary as JSON."""

    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "reports.view"

    def get(self, request):
        report_key = request.query_params.get("report")
        if not report_key:
            raise ValidationError({"report": "A report key is required."})
        filters = _parse_filters(request.query_params)
        try:
            result = run_report(report_key, getattr(request, "tenant", None), filters)
        except KeyError:
            raise ValidationError({"report": f"Unknown report '{report_key}'."})
        return Response({
            "report": report_key,
            "generated_at": timezone.now(),
            "columns": result.columns,
            "rows": result.rows,
            "summary": result.summary,
            "row_count": len(result.rows),
        })


class ReportExportView(APIView):
    """Run a report and return it as a CSV or XLSX download."""

    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "reports.view"

    def get(self, request):
        report_key = request.query_params.get("report")
        if not report_key:
            raise ValidationError({"report": "A report key is required."})
        # NB: don't read `?format=` here — DRF reserves that name for
        # content negotiation and returns 404 if no renderer matches the
        # value ("csv"/"xlsx" aren't registered renderers).
        fmt = (request.query_params.get("fmt") or "csv").lower()
        if fmt not in {"csv", "xlsx"}:
            raise ValidationError({"fmt": "fmt must be 'csv' or 'xlsx'."})
        filters = _parse_filters(request.query_params)
        try:
            result = run_report(report_key, getattr(request, "tenant", None), filters)
        except KeyError:
            raise ValidationError({"report": f"Unknown report '{report_key}'."})

        record_audit(
            AuditAction.EXPORT, "reports.report", entity_id=report_key,
            description=f"Exported report '{report_key}' as {fmt.upper()}",
        )
        filename = f"{report_key}_{timezone.now():%Y%m%d}"
        return export_report(result, fmt, filename)


class DashboardView(APIView):
    """Return role-based dashboard metrics for the requested audience."""

    permission_classes = [IsAuthenticated, HasTenant]

    def get(self, request):
        audience = request.query_params.get("audience", DashboardAudience.EMPLOYEE)
        tenant = getattr(request, "tenant", None)
        user = request.user

        if audience == DashboardAudience.HR:
            self._require(user, tenant, "reports.view")
            data = dashboards.hr_dashboard(tenant)
        elif audience == DashboardAudience.EXECUTIVE:
            self._require(user, tenant, "reports.view_executive")
            data = dashboards.executive_dashboard(tenant)
        elif audience == DashboardAudience.MANAGER:
            data = dashboards.manager_dashboard(tenant, _own_employee(request))
        elif audience == DashboardAudience.EMPLOYEE:
            data = dashboards.employee_dashboard(
                tenant, _own_employee(request), user
            )
        else:
            raise ValidationError({"audience": f"Unknown audience '{audience}'."})
        return Response({"audience": audience, "metrics": data})

    @staticmethod
    def _require(user, tenant, codename):
        if getattr(user, "is_platform_admin", False):
            return
        if not user.has_perm_code(codename, tenant):
            raise PermissionDenied(
                f"This dashboard requires the '{codename}' permission."
            )


class SavedReportViewSet(TenantModelViewSet):
    """CRUD over saved report configurations.

    A user sees their own saved reports plus any shared in the tenant;
    edits and deletes are restricted to the owner.
    """

    queryset = SavedReport.objects.select_related("owner")
    serializer_class = SavedReportSerializer
    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "reports.view"
    filterset_fields = ["report_key", "is_shared"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(
            Q(owner=self.request.user) | Q(is_shared=True)
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.get_tenant(), owner=self.request.user)

    def _assert_owner(self, instance):
        if instance.owner_id != self.request.user.id:
            raise PermissionDenied("You may only modify your own saved reports.")

    def perform_update(self, serializer):
        self._assert_owner(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._assert_owner(instance)
        super().perform_destroy(instance)
