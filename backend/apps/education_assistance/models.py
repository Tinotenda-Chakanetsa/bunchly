"""Education-assistance / school-fees models (spec §9.12).

Five tenant-owned models:

``EducationBenefitRule``    the configurable eligibility-rules engine.
``Dependant``               an employee's registered child / ward.
``EducationClaim``          a school-fees claim moving HR -> Finance.
``EducationClaimDocument``  a supporting file on a claim.
``EducationClaimApproval``  an append-only log of each decision stage.

Rules are never hard-coded — a tenant configures eligibility, caps and
required documents on ``EducationBenefitRule``.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import (
    AcademicPeriodType,
    ClaimApprovalDecision,
    ClaimApprovalStage,
    ClaimDocumentType,
    ClaimStatus,
    DependantRelationship,
    EducationLevel,
)

ZERO = Decimal("0.00")


class EducationBenefitRule(TenantOwnedModel):
    """The configurable eligibility-rules engine for a tenant (spec §9.12 A)."""

    name = models.CharField(max_length=120, default="Education Assistance Policy")
    max_children = models.PositiveSmallIntegerField(
        default=2, help_text="Max children per employee eligible for the benefit."
    )
    covered_levels = models.JSONField(
        default=list,
        blank=True,
        help_text="Education levels covered (empty = all).",
    )
    max_amount_per_child = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO,
        help_text="Maximum claimable amount per child per period.",
    )
    currency = models.CharField(max_length=3, default="GBP")
    frequency = models.CharField(
        max_length=10, choices=AcademicPeriodType.choices,
        default=AcademicPeriodType.TERM,
    )
    eligible_employment_statuses = models.JSONField(
        default=list,
        blank=True,
        help_text="Employment statuses eligible to claim (empty = all).",
    )
    require_probation_passed = models.BooleanField(default=True)
    max_child_age = models.PositiveSmallIntegerField(
        default=0, help_text="Maximum eligible child age; 0 = no limit."
    )
    max_claims_per_period = models.PositiveSmallIntegerField(
        default=1, help_text="Approved claims allowed per employee per period."
    )
    required_documents = models.JSONField(
        default=list,
        blank=True,
        help_text="ClaimDocumentType values required before submission.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.tenant_id})"


class Dependant(TenantOwnedModel):
    """An employee's registered child / ward (spec §9.12 B)."""

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="dependants"
    )
    full_name = models.CharField(max_length=160)
    date_of_birth = models.DateField()
    relationship = models.CharField(
        max_length=12, choices=DependantRelationship.choices,
        default=DependantRelationship.CHILD,
    )
    education_level = models.CharField(
        max_length=12, choices=EducationLevel.choices, blank=True
    )
    institution_name = models.CharField(max_length=200, blank=True)
    student_number = models.CharField(max_length=80, blank=True)
    birth_certificate = models.FileField(
        upload_to="dependant-documents/", null=True, blank=True
    )
    is_benefit_eligible = models.BooleanField(default=True)
    eligibility_override_reason = models.CharField(
        max_length=255, blank=True,
        help_text="Audit reason when HR overrides an eligibility flag.",
    )

    class Meta:
        ordering = ["full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "employee", "full_name", "date_of_birth"],
                name="uniq_dependant_per_employee",
            )
        ]
        indexes = [models.Index(fields=["tenant", "employee"])]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_relationship_display()})"


class EducationClaim(TenantOwnedModel):
    """A school-fees / education-assistance claim (spec §9.12 C, D)."""

    reference = models.CharField(max_length=40, db_index=True)
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="education_claims"
    )
    dependant = models.ForeignKey(
        Dependant, on_delete=models.PROTECT, related_name="claims"
    )
    academic_period = models.CharField(
        max_length=60, help_text="e.g. '2026 Term 1'."
    )
    period_type = models.CharField(
        max_length=10, choices=AcademicPeriodType.choices,
        default=AcademicPeriodType.TERM,
    )
    education_level = models.CharField(
        max_length=12, choices=EducationLevel.choices
    )
    institution_name = models.CharField(max_length=200)
    amount_claimed = models.DecimalField(max_digits=12, decimal_places=2)
    amount_approved = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default="GBP")

    status = models.CharField(
        max_length=12, choices=ClaimStatus.choices,
        default=ClaimStatus.DRAFT, db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    # HR review trail.
    hr_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    hr_reviewed_at = models.DateTimeField(null=True, blank=True)
    hr_note = models.CharField(max_length=255, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    # Finance / payment trail.
    payment_reference = models.CharField(max_length=80, blank=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "employee", "status"]),
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "dependant", "academic_period"]),
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.employee} ({self.get_status_display()})"

    @property
    def payable_amount(self) -> Decimal:
        """Amount to pay — the HR-approved figure, else the claimed amount."""
        return self.amount_approved if self.amount_approved is not None else self.amount_claimed


class EducationClaimDocument(TenantOwnedModel):
    """A supporting document attached to an education claim."""

    claim = models.ForeignKey(
        EducationClaim, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(
        max_length=24, choices=ClaimDocumentType.choices,
        default=ClaimDocumentType.OTHER,
    )
    file = models.FileField(upload_to="education-claim-documents/")
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "claim"])]

    def __str__(self) -> str:
        return f"{self.get_doc_type_display()} — {self.claim.reference}"


class EducationClaimApproval(TenantOwnedModel):
    """An append-only record of one decision on a claim (spec §9.12 D)."""

    claim = models.ForeignKey(
        EducationClaim, on_delete=models.CASCADE, related_name="approvals"
    )
    stage = models.CharField(max_length=16, choices=ClaimApprovalStage.choices)
    decision = models.CharField(max_length=16, choices=ClaimApprovalDecision.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["tenant", "claim", "created_at"])]

    def __str__(self) -> str:
        return f"{self.get_stage_display()}: {self.get_decision_display()}"
