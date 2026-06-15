"""Payroll models (spec §9.10).

The module implements *payroll-ready data structures* rather than a full
statutory payroll engine:

``PayrollPeriod``   a pay run for a date range, with its own status flow.
``PayComponent``    a tenant-configurable allowance / deduction definition.
``PayrollRecord``   one employee's pay for a period — salary snapshot,
                    leave-without-pay and computed gross / net.
``PayrollLine``     an allowance / deduction line on a record.
``Payslip``         a frozen, employee-visible breakdown of a record.

Compensation figures are sensitive: viewset scoping confines records and
payslips to the owning employee and ``payroll`` permission holders.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import ComponentType, PayrollStatus, RecordStatus

ZERO = Decimal("0.00")


class PayrollPeriod(TenantOwnedModel):
    """A pay run covering a date range (spec §9.10 — payroll period setup)."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40, help_text="e.g. '2026-05'.")
    start_date = models.DateField()
    end_date = models.DateField()
    pay_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=12,
        choices=PayrollStatus.choices,
        default=PayrollStatus.DRAFT,
        db_index=True,
    )
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_payrollperiod_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "status"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class PayComponent(TenantOwnedModel):
    """A configurable allowance or deduction definition for a tenant."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    component_type = models.CharField(
        max_length=10, choices=ComponentType.choices, default=ComponentType.ALLOWANCE
    )
    is_taxable = models.BooleanField(default=True)
    default_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO,
        help_text="Suggested amount when adding this component to a record.",
    )
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["component_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_paycomponent_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_component_type_display()})"


class PayrollRecord(TenantOwnedModel):
    """One employee's pay for a period.

    ``basic_salary`` is snapshotted from the employee at generation time.
    ``gross_pay`` / ``net_pay`` and the allowance/deduction totals are
    derived by ``services.recalculate_record`` — never set directly.
    """

    period = models.ForeignKey(
        PayrollPeriod, on_delete=models.CASCADE, related_name="records"
    )
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="payroll_records"
    )
    currency = models.CharField(max_length=3, default="GBP")
    basic_salary = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)

    total_allowances = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO
    )
    total_deductions = models.DecimalField(
        max_digits=14, decimal_places=2, default=ZERO
    )
    overtime_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO,
        help_text="Imported / entered overtime pay for the period.",
    )
    leave_without_pay_days = models.DecimalField(
        max_digits=6, decimal_places=2, default=ZERO
    )
    leave_without_pay_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO
    )
    gross_pay = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    net_pay = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)

    status = models.CharField(
        max_length=10,
        choices=RecordStatus.choices,
        default=RecordStatus.DRAFT,
        db_index=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["employee__first_name", "employee__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "period", "employee"],
                name="uniq_payrollrecord_per_period_employee",
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "period", "status"]),
            models.Index(fields=["tenant", "employee"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} — {self.period.code}"


class PayrollLine(TenantOwnedModel):
    """An allowance or deduction line on a payroll record."""

    record = models.ForeignKey(
        PayrollRecord, on_delete=models.CASCADE, related_name="lines"
    )
    component = models.ForeignKey(
        PayComponent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lines",
    )
    line_type = models.CharField(max_length=10, choices=ComponentType.choices)
    description = models.CharField(max_length=160)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    is_taxable = models.BooleanField(default=True)

    class Meta:
        ordering = ["line_type", "description"]
        indexes = [models.Index(fields=["tenant", "record"])]

    def __str__(self) -> str:
        return f"{self.description}: {self.amount}"


class Payslip(TenantOwnedModel):
    """A frozen, employee-visible breakdown of a payroll record."""

    record = models.OneToOneField(
        PayrollRecord, on_delete=models.CASCADE, related_name="payslip"
    )
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="payslips"
    )
    period = models.ForeignKey(
        PayrollPeriod, on_delete=models.CASCADE, related_name="payslips"
    )
    reference = models.CharField(max_length=40, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    # Frozen breakdown captured at generation — survives later record edits.
    snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "employee", "is_published"]),
            models.Index(fields=["tenant", "period"]),
        ]

    def __str__(self) -> str:
        return f"Payslip {self.reference} — {self.employee}"
