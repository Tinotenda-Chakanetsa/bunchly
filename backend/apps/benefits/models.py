"""Benefits-administration models (spec §9.11).

``BenefitType``              a tenant-configurable benefit definition —
                             category, provider, contributions, eligibility.
``EmployeeBenefit``          an employee's enrolment in a benefit type.
``BenefitEnrolmentHistory``  an append-only log of enrolment changes.

Education assistance / school-fees is its own specialised module
(``apps.education_assistance``); this module covers the general benefit
catalogue and enrolment lifecycle. ``BenefitType.pay_component`` links a
benefit to a payroll deduction so contributions can flow into payroll.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import (
    BenefitCategory,
    ContributionBasis,
    EnrolmentEvent,
    EnrolmentStatus,
)

ZERO = Decimal("0.00")


class BenefitType(TenantOwnedModel):
    """A configurable benefit a tenant offers (spec §9.11 — benefit types)."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    category = models.CharField(
        max_length=20, choices=BenefitCategory.choices, default=BenefitCategory.OTHER
    )
    description = models.TextField(blank=True)
    provider = models.CharField(max_length=160, blank=True)

    contribution_basis = models.CharField(
        max_length=12, choices=ContributionBasis.choices,
        default=ContributionBasis.FIXED,
    )
    employee_contribution = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO,
        help_text="Amount, or percentage of basic salary, per the basis.",
    )
    employer_contribution = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO,
        help_text="Amount, or percentage of basic salary, per the basis.",
    )
    is_taxable = models.BooleanField(default=False)

    # Eligibility rules — configurable, never hard-coded.
    requires_approval = models.BooleanField(
        default=True, help_text="Enrolments need HR approval before they activate."
    )
    covers_dependants = models.BooleanField(default=False)
    eligibility_min_months = models.PositiveSmallIntegerField(
        default=0, help_text="Months of service required before enrolling."
    )
    eligible_employment_statuses = models.JSONField(
        default=list,
        blank=True,
        help_text="Employment statuses eligible to enrol (empty = all).",
    )

    # Optional link to a payroll deduction component.
    pay_component = models.ForeignKey(
        "payroll.PayComponent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="benefit_types",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["category", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_benefittype_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_category_display()})"


class EmployeeBenefit(TenantOwnedModel):
    """An employee's enrolment in a benefit type (spec §9.11 — enrolment)."""

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="benefits"
    )
    benefit_type = models.ForeignKey(
        BenefitType, on_delete=models.PROTECT, related_name="enrolments"
    )
    status = models.CharField(
        max_length=12,
        choices=EnrolmentStatus.choices,
        default=EnrolmentStatus.PENDING,
        db_index=True,
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Contribution amounts — snapshot from the benefit type, overridable.
    employee_contribution = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO
    )
    employer_contribution = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO
    )
    covered_dependants = models.ManyToManyField(
        "education_assistance.Dependant",
        blank=True,
        related_name="benefit_enrolments",
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
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "employee", "status"]),
            models.Index(fields=["tenant", "benefit_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} — {self.benefit_type.name}"


class BenefitEnrolmentHistory(TenantOwnedModel):
    """An append-only record of a change to a benefit enrolment."""

    enrolment = models.ForeignKey(
        EmployeeBenefit, on_delete=models.CASCADE, related_name="history"
    )
    event = models.CharField(max_length=16, choices=EnrolmentEvent.choices)
    note = models.CharField(max_length=255, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "Benefit enrolment history"
        indexes = [models.Index(fields=["tenant", "enrolment", "created_at"])]

    def __str__(self) -> str:
        return f"{self.get_event_display()} — {self.enrolment_id}"
