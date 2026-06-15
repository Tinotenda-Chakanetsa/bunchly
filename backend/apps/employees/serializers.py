"""Serializers for the employees / core-HR module.

Sensitive compensation fields are removed from the payload unless the
requesting user holds the ``employees.view_salary`` permission.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import (
    Employee,
    EmployeeHistory,
    EmergencyContact,
    EmploymentContract,
)

# Compensation / bank / tax fields — shown only to authorised roles.
SENSITIVE_FIELDS = (
    "bank_name",
    "bank_account_name",
    "bank_account_number",
    "bank_branch_code",
    "tax_number",
    "tax_code",
    "current_salary",
    "salary_currency",
)


class EmployeeListSerializer(serializers.ModelSerializer):
    """Lightweight row for employee-directory list views."""

    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    job_title_name = serializers.CharField(source="job_title.name", read_only=True, default=None)
    work_location_name = serializers.CharField(
        source="work_location.name", read_only=True, default=None
    )
    line_manager_name = serializers.CharField(
        source="line_manager.full_name", read_only=True, default=None
    )

    class Meta:
        model = Employee
        fields = [
            "id", "employee_number", "full_name", "preferred_name",
            "work_email", "photo", "department", "department_name",
            "job_title", "job_title_name", "work_location",
            "work_location_name", "line_manager", "line_manager_name",
            "employment_type", "employment_status", "start_date",
        ]


class EmployeeSerializer(TenantScopedModelSerializer):
    """Full employee record — salary/bank/tax fields are RBAC-gated."""

    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    position_name = serializers.CharField(source="position.name", read_only=True, default=None)
    job_title_name = serializers.CharField(source="job_title.name", read_only=True, default=None)
    grade_name = serializers.CharField(source="grade.name", read_only=True, default=None)
    work_location_name = serializers.CharField(
        source="work_location.name", read_only=True, default=None
    )
    line_manager_name = serializers.CharField(
        source="line_manager.full_name", read_only=True, default=None
    )

    class Meta:
        model = Employee
        fields = [
            "id", "user", "employee_number", "first_name", "last_name",
            "preferred_name", "full_name", "gender", "date_of_birth",
            "marital_status", "photo", "national_id", "passport_number",
            "personal_email", "work_email", "phone", "alternate_phone",
            "address_line1", "address_line2", "city", "state", "postal_code",
            "country", "department", "department_name", "position",
            "position_name", "job_title", "job_title_name", "grade",
            "grade_name", "cost_centre", "work_location", "work_location_name",
            "line_manager", "line_manager_name", "employment_type",
            "employment_status", "start_date", "confirmation_date",
            "probation_end_date", "contract_start_date", "contract_end_date",
            "retirement_date", "end_date", "exit_reason", "benefits_eligible",
            "notes", "created_at", "updated_at",
            # Sensitive (gated below):
            *SENSITIVE_FIELDS,
        ]
        read_only_fields = ["created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        tenant = getattr(request, "tenant", None)
        can_see_salary = bool(
            user
            and user.is_authenticated
            and user.has_perm_code("employees.view_salary", tenant)
        )
        if not can_see_salary:
            for field in SENSITIVE_FIELDS:
                self.fields.pop(field, None)

    def validate_employee_number(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        # Check against all rows (incl. soft-deleted) — the DB constraint does.
        qs = Employee.all_objects.filter(tenant=tenant, employee_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "An employee with this number already exists."
            )
        return value

    def validate_line_manager(self, value):
        if value and self.instance and value.pk == self.instance.pk:
            raise serializers.ValidationError("An employee cannot manage themselves.")
        return value


class EmergencyContactSerializer(TenantScopedModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = [
            "id", "employee", "name", "relationship", "phone",
            "alternate_phone", "email", "address", "is_primary", "created_at",
        ]


class EmploymentContractSerializer(TenantScopedModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = EmploymentContract
        fields = [
            "id", "employee", "employee_name", "reference", "contract_type",
            "status", "job_title", "start_date", "end_date", "signed_date",
            "document", "notes", "created_at",
        ]


class ContractTemplateSerializer(TenantScopedModelSerializer):
    """A tenant-uploaded .docx mail-merge template."""

    # Declared explicitly so a JSON or PATCH caller that omits either flag
    # falls back to the documented default. (Note: DRF's BooleanField still
    # coerces a missing multipart field to False — clients posting form-data
    # must send `is_active` explicitly, which contracts.ts now does.)
    is_active = serializers.BooleanField(required=False, default=True)
    is_default = serializers.BooleanField(required=False, default=False)

    class Meta:
        from .models import ContractTemplate

        model = ContractTemplate
        fields = [
            "id", "name", "code", "description", "template_file",
            "discovered_placeholders",
            "is_default", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = [
            "discovered_placeholders", "created_at", "updated_at",
        ]

    def validate_code(self, value):
        from .models import ContractTemplate

        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = ContractTemplate.all_objects.filter(tenant=tenant, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A contract template with this code already exists."
            )
        return value


class EmployeeHistorySerializer(serializers.ModelSerializer):
    change_type_display = serializers.CharField(
        source="get_change_type_display", read_only=True
    )

    class Meta:
        model = EmployeeHistory
        fields = [
            "id", "employee", "change_type", "change_type_display",
            "effective_date", "field_changed", "previous_value", "new_value",
            "reason", "created_at",
        ]
        read_only_fields = fields
