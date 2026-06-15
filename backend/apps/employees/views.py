"""Viewsets for the employees / core-HR module.

Access scoping:
- ``employees.view_employee``  -> sees all employees in the tenant.
- ``employees.view_team``      -> sees own record + direct reports.
- otherwise                    -> sees only their own record.

Every create/update/exit is mirrored into ``EmployeeHistory`` (the change
log) and the audit trail.
"""
from __future__ import annotations

from django.core.files.base import ContentFile
from django.http import FileResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.permissions import HasModulePermission, HasTenant
from apps.common.viewsets import TenantModelViewSet

from .enums import ChangeType, EmploymentStatus
from .models import (
    ContractTemplate,
    Employee,
    EmployeeHistory,
    EmergencyContact,
    EmploymentContract,
)
from .serializers import (
    ContractTemplateSerializer,
    EmployeeHistorySerializer,
    EmployeeListSerializer,
    EmployeeSerializer,
    EmergencyContactSerializer,
    EmploymentContractSerializer,
)

# Employee fields whose changes are recorded in EmployeeHistory.
TRACKED_FIELDS: dict[str, str] = {
    "department": ChangeType.DEPARTMENT_TRANSFER,
    "position": ChangeType.POSITION_CHANGE,
    "job_title": ChangeType.POSITION_CHANGE,
    "grade": ChangeType.GRADE_CHANGE,
    "line_manager": ChangeType.MANAGER_CHANGE,
    "employment_status": ChangeType.STATUS_CHANGE,
    "employment_type": ChangeType.CONTRACT_CHANGE,
    "current_salary": ChangeType.SALARY_CHANGE,
    "contract_end_date": ChangeType.CONTRACT_CHANGE,
}


def _log_history(employee, change_type, *, field="", before=None, after=None, reason=""):
    EmployeeHistory.objects.create(
        tenant=employee.tenant,
        employee=employee,
        change_type=change_type,
        effective_date=timezone.now().date(),
        field_changed=field,
        previous_value="" if before is None else str(before),
        new_value="" if after is None else str(after),
        reason=reason,
    )


class EmployeeViewSet(TenantModelViewSet):
    """Employee master data — directory, profile, lifecycle actions."""

    queryset = Employee.objects.select_related(
        "department", "position", "job_title", "grade", "work_location",
        "cost_centre", "line_manager", "user",
    )
    # list/retrieve are role-scoped in get_queryset; writes need RBAC.
    permission_required = {
        "create": "employees.add_employee",
        "update": "employees.change_employee",
        "partial_update": "employees.change_employee",
        "destroy": "employees.archive_employee",
        "terminate": "employees.archive_employee",
        "reinstate": "employees.change_employee",
    }
    search_fields = ["first_name", "last_name", "employee_number", "work_email"]
    filterset_fields = ["employment_status", "employment_type", "department", "grade"]
    ordering_fields = ["first_name", "last_name", "start_date", "created_at"]

    def get_serializer_class(self):
        return EmployeeListSerializer if self.action == "list" else EmployeeSerializer

    def get_queryset(self):
        # Tenant scoping is applied by TenantScopedViewSetMixin.
        queryset = super().get_queryset()
        user = self.request.user
        tenant = getattr(self.request, "tenant", None)

        if user.has_perm_code("employees.view_employee", tenant):
            return queryset

        own = queryset.filter(user=user)
        if user.has_perm_code("employees.view_team", tenant):
            # Manager: own record plus direct reports.
            self_emp = own.first()
            if self_emp is not None:
                return queryset.filter(
                    id__in=[self_emp.id]
                ) | queryset.filter(line_manager=self_emp)
            return own
        # Plain employee: own record only (self-service).
        return own

    def perform_create(self, serializer):
        super().perform_create(serializer)
        employee = serializer.instance
        _log_history(
            employee,
            ChangeType.HIRE,
            reason="Employee record created.",
        )
        record_audit(
            AuditAction.CREATE,
            "employees.employee",
            entity_id=employee.pk,
            description=f"Created employee {employee.full_name}",
        )

    def perform_update(self, serializer):
        employee = serializer.instance
        before = {field: getattr(employee, field) for field in TRACKED_FIELDS}
        serializer.save()  # updates `employee` in place

        for field, change_type in TRACKED_FIELDS.items():
            old_value, new_value = before[field], getattr(employee, field)
            if old_value != new_value:
                _log_history(
                    employee,
                    change_type,
                    field=field,
                    before=old_value,
                    after=new_value,
                )
        record_audit(
            AuditAction.UPDATE,
            "employees.employee",
            entity_id=employee.pk,
            description=f"Updated employee {employee.full_name}",
        )

    def perform_destroy(self, instance):
        pk, name = instance.pk, instance.full_name
        super().perform_destroy(instance)  # soft delete
        record_audit(
            AuditAction.DELETE,
            "employees.employee",
            entity_id=pk,
            description=f"Archived employee {name}",
        )

    @action(detail=False, methods=["get"])
    def me(self, request):
        """The requesting user's own employee record (self-service)."""
        tenant = getattr(request, "tenant", None)
        employee = (
            Employee.objects.filter(tenant=tenant, user=request.user)
            .select_related("department", "job_title", "line_manager")
            .first()
        )
        if employee is None:
            raise NotFound("You do not have an employee profile in this organisation.")
        return Response(EmployeeSerializer(employee, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """Change history for an employee."""
        employee = self.get_object()
        page = self.paginate_queryset(employee.history.all())
        serializer = EmployeeHistorySerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"], url_path="direct-reports")
    def direct_reports(self, request, pk=None):
        """Employees who report to this employee."""
        employee = self.get_object()
        reports = self.get_queryset().filter(line_manager=employee)
        page = self.paginate_queryset(reports)
        serializer = EmployeeListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        """Terminate / exit an employee (sets status, exit date and reason)."""
        employee = self.get_object()
        new_status = request.data.get("status", EmploymentStatus.TERMINATED)
        if new_status not in EmploymentStatus.values:
            raise ValidationError({"status": "Invalid employment status."})
        reason = request.data.get("reason", "")
        end_date = request.data.get("end_date") or timezone.now().date()

        old_status = employee.employment_status
        employee.employment_status = new_status
        employee.end_date = end_date
        employee.exit_reason = reason
        employee.save(update_fields=["employment_status", "end_date", "exit_reason", "updated_at"])

        _log_history(
            employee, ChangeType.EXIT, field="employment_status",
            before=old_status, after=new_status, reason=reason,
        )
        record_audit(
            AuditAction.UPDATE, "employees.employee", entity_id=employee.pk,
            description=f"Terminated employee {employee.full_name}", reason=reason,
        )
        return Response(EmployeeSerializer(employee, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def reinstate(self, request, pk=None):
        """Reinstate a previously exited employee."""
        employee = self.get_object()
        old_status = employee.employment_status
        employee.employment_status = EmploymentStatus.ACTIVE
        employee.end_date = None
        employee.exit_reason = ""
        employee.save(update_fields=["employment_status", "end_date", "exit_reason", "updated_at"])

        _log_history(
            employee, ChangeType.STATUS_CHANGE, field="employment_status",
            before=old_status, after=EmploymentStatus.ACTIVE,
            reason="Employee reinstated.",
        )
        record_audit(
            AuditAction.UPDATE, "employees.employee", entity_id=employee.pk,
            description=f"Reinstated employee {employee.full_name}",
        )
        return Response(EmployeeSerializer(employee, context={"request": request}).data)


class EmergencyContactViewSet(TenantModelViewSet):
    """Emergency contacts for employees."""

    queryset = EmergencyContact.objects.select_related("employee")
    serializer_class = EmergencyContactSerializer
    permission_required = {
        "create": "employees.change_employee",
        "update": "employees.change_employee",
        "partial_update": "employees.change_employee",
        "destroy": "employees.change_employee",
    }
    filterset_fields = ["employee", "is_primary"]


class EmploymentContractViewSet(TenantModelViewSet):
    """Employment contracts held by employees."""

    queryset = EmploymentContract.objects.select_related("employee")
    serializer_class = EmploymentContractSerializer
    permission_required = {
        "create": "employees.change_employee",
        "update": "employees.change_employee",
        "partial_update": "employees.change_employee",
        "destroy": "employees.change_employee",
    }
    filterset_fields = ["employee", "status", "contract_type"]
    ordering_fields = ["start_date", "end_date", "created_at"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE, "employees.contract",
            entity_id=serializer.instance.pk,
            description="Created employment contract",
        )

    @action(detail=True, methods=["post"], url_path="generate")
    def generate(self, request, pk=None):
        """Generate a ``.docx`` employment contract from this record.

        Employer branding is pulled from the tenant + System Settings; the
        employee + role data comes from the contract record. The caller
        may pass overrides — e.g. ``witness_name``, ``signed_by``,
        ``annual_leave_text`` — to customise this generation only.
        The generated file is stored on the contract's ``document``
        field (so it can be re-downloaded) and returned as an attachment.
        """
        from .contract_generator import generate as generate_contract
        from .contract_generator import resolve_template

        contract = self.get_object()
        overrides = (
            dict(request.data) if isinstance(request.data, dict) else {}
        )
        template_id = overrides.pop("template_id", None) or overrides.pop(
            "template", None
        )
        template = resolve_template(contract, template_id=template_id)
        try:
            buffer = generate_contract(
                contract, overrides=overrides, template=template,
            )
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(
                {"detail": f"Could not generate contract: {exc}"}
            )

        safe_name = (
            contract.employee.full_name.replace(" ", "_").replace("/", "-")
            or "contract"
        )
        filename = (
            f"Contract_{safe_name}_{contract.start_date or 'draft'}.docx"
        )
        # Persist on the contract for re-download.
        contract.document.save(
            filename, ContentFile(buffer.getvalue()), save=False
        )
        contract.save(update_fields=["document", "updated_at"])

        record_audit(
            AuditAction.DOWNLOAD, "employees.contract", entity_id=contract.pk,
            description=f"Generated contract document for "
                        f"{contract.employee.full_name}",
        )

        buffer.seek(0)
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        )


class ContractTemplateViewSet(TenantModelViewSet):
    """Per-tenant contract templates (.docx with ``{{ placeholders }}``).

    Tenants upload their own legal-team-approved template; the generator
    mail-merges into it instead of using the built-in layout. Exactly
    one template per tenant should be ``is_default=True``; ``perform_create``
    / ``perform_update`` enforce that.
    """

    queryset = ContractTemplate.objects.all()
    serializer_class = ContractTemplateSerializer
    permission_required = {
        "create": "employees.change_employee",
        "update": "employees.change_employee",
        "partial_update": "employees.change_employee",
        "destroy": "employees.change_employee",
    }
    filterset_fields = ["is_active", "is_default"]
    search_fields = ["name", "code"]

    def _enforce_single_default(self, instance: ContractTemplate) -> None:
        if not instance.is_default:
            return
        ContractTemplate.objects.filter(
            tenant=instance.tenant, is_default=True
        ).exclude(pk=instance.pk).update(is_default=False)

    def _scan_placeholders(self, instance: ContractTemplate) -> None:
        """Parse the uploaded .docx and persist its token list on the row."""
        if not instance.template_file:
            return
        from .contract_generator import parse_template_placeholders

        try:
            tokens = parse_template_placeholders(instance.template_file)
        except Exception:  # noqa: BLE001 — corrupt upload, leave list empty
            tokens = []
        if instance.discovered_placeholders != tokens:
            instance.discovered_placeholders = tokens
            instance.save(update_fields=["discovered_placeholders", "updated_at"])

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._enforce_single_default(serializer.instance)
        self._scan_placeholders(serializer.instance)
        record_audit(
            AuditAction.UPLOAD, "employees.contract_template",
            entity_id=serializer.instance.pk,
            description=(
                f"Uploaded contract template '{serializer.instance.name}'"
            ),
        )

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._enforce_single_default(serializer.instance)
        # Re-scan if the file changed.
        if "template_file" in serializer.validated_data:
            self._scan_placeholders(serializer.instance)

    @action(detail=False)
    def placeholders(self, request):
        """The system's full catalogue of auto-fillable ``{{ tokens }}``.

        Useful as a reference HR can paste at the bottom of their Word
        template while authoring it.
        """
        from .contract_generator import available_placeholders

        return Response({"placeholders": available_placeholders()})

    @action(detail=True)
    def tokens(self, request, pk=None):
        """Classify this template's placeholders into auto vs manual.

        ``auto`` — names the system can fill from the tenant/employee/
        contract context. ``manual`` — names only the template knows; HR
        must supply values at generation time. ``all`` — every unique
        token discovered when the file was uploaded.
        """
        from .contract_generator import classify_template_placeholders

        template = self.get_object()
        return Response(
            classify_template_placeholders(template.discovered_placeholders)
        )

    @action(detail=True)
    def preview(self, request, pk=None):
        """Pre-resolve a template's placeholders against an employee.

        Used by the New Contract dialog to populate every input the
        template needs. Accepts ?employee=<uuid>, plus optional
        ?contract_type=&start_date=&end_date=&job_title= so dynamic
        tokens like ``formatted_start_date`` reflect the form's current
        state. Returns ``{tokens, values, template_name}``.
        """
        from datetime import date

        from .contract_generator import build_context

        template = self.get_object()
        tenant = getattr(request, "tenant", None)
        employee = Employee.objects.filter(
            tenant=tenant, pk=request.query_params.get("employee")
        ).first()
        if employee is None:
            return Response(
                {"detail": "Employee not found."}, status=404
            )

        def _parse(value):
            try:
                return date.fromisoformat(value) if value else None
            except (TypeError, ValueError):
                return None

        # An unsaved stub so build_context can resolve everything that
        # depends on contract fields without a row existing yet.
        stub = EmploymentContract(
            tenant=tenant, employee=employee,
            contract_type=(
                request.query_params.get("contract_type") or "full_time"
            ),
            start_date=_parse(request.query_params.get("start_date")),
            end_date=_parse(request.query_params.get("end_date")),
            job_title=request.query_params.get("job_title", ""),
        )
        context = build_context(stub)
        tokens = list(template.discovered_placeholders or [])
        values = {
            tok: ("" if context.get(tok) is None else str(context.get(tok)))
            for tok in tokens
        }
        return Response({
            "template_name": template.name,
            "tokens": tokens,
            "values": values,
        })


class EmployeeHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only employee change history."""

    serializer_class = EmployeeHistorySerializer
    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "employees.view_employee"
    filterset_fields = ["employee", "change_type"]
    ordering_fields = ["created_at", "effective_date"]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        return EmployeeHistory.objects.filter(tenant=tenant).select_related("employee")
