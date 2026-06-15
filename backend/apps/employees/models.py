"""Core HR / employee master-data models (spec §9.1).

The ``Employee`` record is the central source of truth for a person.
Sensitive fields (salary, bank, tax, national ID) are stored here but
exposed only to authorised roles by the serializer layer; in production
column-level encryption / encrypted storage should back these fields.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import (
    ChangeType,
    ContractStatus,
    EmploymentStatus,
    EmploymentType,
    Gender,
    MaritalStatus,
)


class Employee(TenantOwnedModel):
    """A person employed by the tenant — the core HR record."""

    # --- Account link -----------------------------------------------------
    # Optional: an employee may exist before they have a login account.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )
    employee_number = models.CharField(max_length=40, db_index=True)

    # --- Personal details -------------------------------------------------
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    preferred_name = models.CharField(max_length=120, blank=True)
    gender = models.CharField(
        max_length=20, choices=Gender.choices, default=Gender.UNDISCLOSED
    )
    date_of_birth = models.DateField(null=True, blank=True, db_index=True)
    marital_status = models.CharField(
        max_length=20, choices=MaritalStatus.choices, blank=True
    )
    photo = models.ImageField(upload_to="employee-photos/", null=True, blank=True)

    # --- Sensitive identity (gated by RBAC at the serializer) ------------
    national_id = models.CharField(max_length=60, blank=True)
    passport_number = models.CharField(max_length=60, blank=True)

    # --- Contact ----------------------------------------------------------
    personal_email = models.EmailField(blank=True)
    work_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    alternate_phone = models.CharField(max_length=32, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=40, blank=True)
    country = models.CharField(max_length=80, blank=True)

    # --- Organisation placement ------------------------------------------
    department = models.ForeignKey(
        "organisation.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    position = models.ForeignKey(
        "organisation.Position",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    job_title = models.ForeignKey(
        "organisation.JobTitle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    grade = models.ForeignKey(
        "organisation.Grade",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    cost_centre = models.ForeignKey(
        "organisation.CostCentre",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    work_location = models.ForeignKey(
        "organisation.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    line_manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
    )

    # --- Employment -------------------------------------------------------
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.PROBATION,
        db_index=True,
    )
    start_date = models.DateField(null=True, blank=True, db_index=True)
    confirmation_date = models.DateField(null=True, blank=True)
    probation_end_date = models.DateField(null=True, blank=True, db_index=True)
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True, db_index=True)
    retirement_date = models.DateField(null=True, blank=True, db_index=True)
    end_date = models.DateField(
        null=True, blank=True, help_text="Actual exit/termination date."
    )
    exit_reason = models.CharField(max_length=255, blank=True)

    # --- Sensitive: bank / tax / salary (gated by RBAC) ------------------
    bank_name = models.CharField(max_length=160, blank=True)
    bank_account_name = models.CharField(max_length=160, blank=True)
    bank_account_number = models.CharField(max_length=64, blank=True)
    bank_branch_code = models.CharField(max_length=40, blank=True)
    tax_number = models.CharField(max_length=60, blank=True)
    tax_code = models.CharField(max_length=40, blank=True)
    current_salary = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    salary_currency = models.CharField(max_length=3, default="GBP")

    benefits_eligible = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["first_name", "last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "employee_number"],
                name="uniq_employee_number_per_tenant",
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "employment_status"]),
            models.Index(fields=["tenant", "department"]),
            models.Index(fields=["tenant", "line_manager"]),
            models.Index(fields=["tenant", "contract_end_date"]),
            models.Index(fields=["tenant", "probation_end_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.employee_number})"

    @property
    def full_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.employee_number

    @property
    def display_name(self) -> str:
        return self.preferred_name or self.first_name


class EmergencyContact(TenantOwnedModel):
    """An emergency contact for an employee."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="emergency_contacts"
    )
    name = models.CharField(max_length=160)
    relationship = models.CharField(max_length=80)
    phone = models.CharField(max_length=32)
    alternate_phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "name"]
        indexes = [models.Index(fields=["tenant", "employee"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.relationship})"


class EmploymentContract(TenantOwnedModel):
    """An employment contract held by an employee."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="contracts"
    )
    reference = models.CharField(max_length=80, blank=True)
    contract_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    status = models.CharField(
        max_length=20, choices=ContractStatus.choices, default=ContractStatus.DRAFT
    )
    job_title = models.CharField(
        max_length=160, blank=True, help_text="Title snapshot at signing."
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, db_index=True)
    signed_date = models.DateField(null=True, blank=True)
    # Document file kept here for now; migrates to the documents module later.
    document = models.FileField(upload_to="contracts/", null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["tenant", "employee"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self) -> str:
        return f"Contract {self.reference or self.pk} — {self.employee}"


class ContractTemplate(TenantOwnedModel):
    """A per-tenant employment-contract template (.docx) for mail-merge.

    HR uploads a Word document containing ``{{ placeholders }}`` (e.g.
    ``{{ employee_name }}``, ``{{ tenure_paragraph }}``); the contract
    generator fills them. If a tenant has no template (or none is
    picked), the generator falls back to the built-in layout in
    ``contract_generator.render_contract`` (which is itself driven by
    the tenant's ``contract.*`` SystemSettings).
    """

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40)
    description = models.TextField(blank=True)
    template_file = models.FileField(upload_to="contract-templates/")
    # Every {{ token }} the uploaded .docx actually uses — parsed once on
    # upload by ``ContractTemplateViewSet.perform_create``. Drives the
    # "ask for what the template needs" UX in the generate dialog.
    discovered_placeholders = models.JSONField(default=list, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                name="uniq_contracttemplate_code_per_tenant",
            ),
        ]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return self.name


class EmployeeHistory(TenantOwnedModel):
    """An append-only record of a change to an employee record.

    Powers the employment / position / salary / transfer / reporting-line
    change history required by spec §9.1.
    """

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="history"
    )
    change_type = models.CharField(max_length=30, choices=ChangeType.choices)
    effective_date = models.DateField(null=True, blank=True)
    field_changed = models.CharField(max_length=80, blank=True)
    previous_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Employee history"
        indexes = [
            models.Index(fields=["tenant", "employee", "created_at"]),
            models.Index(fields=["tenant", "change_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_change_type_display()} — {self.employee}"
