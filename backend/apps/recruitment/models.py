"""Recruitment / applicant-tracking models (spec §9.5).

``JobRequisition``    a request to hire — headcount against an org seat.
``JobPosting``        a published advert derived from a requisition.
``Candidate``         a person's application to a posting; carries the
                      pipeline stage and, once hired, a link to the
                      created ``Employee`` record.
``CandidateDocument`` a CV / certificate / reference file.
``Interview``         a scheduled interview with score and feedback.
``Offer``             an offer with its own draft -> approved -> sent ->
                      accepted lifecycle.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel
from apps.employees.enums import EmploymentType

from .enums import (
    CandidateDocumentType,
    InterviewMode,
    InterviewStatus,
    OfferStatus,
    PostingStatus,
    RecruitmentStage,
    RequisitionStatus,
)

ZERO = Decimal("0.00")


class JobRequisition(TenantOwnedModel):
    """A request to hire for an organisational seat (spec §9.5)."""

    reference = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=200)
    department = models.ForeignKey(
        "organisation.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisitions",
    )
    job_title = models.ForeignKey(
        "organisation.JobTitle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisitions",
    )
    grade = models.ForeignKey(
        "organisation.Grade",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisitions",
    )
    headcount = models.PositiveSmallIntegerField(default=1)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    hiring_manager = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requisitions",
    )
    status = models.CharField(
        max_length=12,
        choices=RequisitionStatus.choices,
        default=RequisitionStatus.DRAFT,
        db_index=True,
    )
    reason = models.TextField(blank=True)
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
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "reference"],
                name="uniq_jobrequisition_reference_per_tenant",
            )
        ]
        indexes = [models.Index(fields=["tenant", "status"])]

    def __str__(self) -> str:
        return f"{self.reference} — {self.title}"


class JobPosting(TenantOwnedModel):
    """A published advert for a requisition (spec §9.5)."""

    requisition = models.ForeignKey(
        JobRequisition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="postings",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.ForeignKey(
        "organisation.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_postings",
    )
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    is_internal = models.BooleanField(
        default=False, help_text="Internal vacancy announcement."
    )
    status = models.CharField(
        max_length=10,
        choices=PostingStatus.choices,
        default=PostingStatus.DRAFT,
        db_index=True,
    )
    posted_date = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "status", "is_internal"])]

    def __str__(self) -> str:
        return self.title


class Candidate(TenantOwnedModel):
    """A person's application to a job posting (spec §9.5)."""

    posting = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name="candidates"
    )
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    source = models.CharField(
        max_length=80, blank=True, help_text="Where the application came from."
    )
    stage = models.CharField(
        max_length=16,
        choices=RecruitmentStage.choices,
        default=RecruitmentStage.APPLIED,
        db_index=True,
    )
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Overall 1-5 rating."
    )
    summary = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    applied_at = models.DateField(null=True, blank=True)
    # Set when the candidate is hired and converted to an employee.
    linked_employee = models.OneToOneField(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_candidate",
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["tenant", "posting", "stage"]),
            models.Index(fields=["tenant", "stage"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} → {self.posting.title}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class CandidateDocument(TenantOwnedModel):
    """A document uploaded for a candidate (CV, certificate, reference)."""

    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(
        max_length=16,
        choices=CandidateDocumentType.choices,
        default=CandidateDocumentType.CV,
    )
    file = models.FileField(upload_to="candidate-documents/")
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "candidate"])]

    def __str__(self) -> str:
        return f"{self.get_doc_type_display()} — {self.candidate.full_name}"


class Interview(TenantOwnedModel):
    """A scheduled interview with its score and feedback (spec §9.5)."""

    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="interviews"
    )
    scheduled_at = models.DateTimeField()
    mode = models.CharField(
        max_length=10, choices=InterviewMode.choices, default=InterviewMode.VIDEO
    )
    location = models.CharField(max_length=255, blank=True)
    interviewers = models.ManyToManyField(
        "employees.Employee", blank=True, related_name="interviews"
    )
    status = models.CharField(
        max_length=10,
        choices=InterviewStatus.choices,
        default=InterviewStatus.SCHEDULED,
        db_index=True,
    )
    score = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Interview score 1-5."
    )
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ["scheduled_at"]
        indexes = [
            models.Index(fields=["tenant", "candidate"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self) -> str:
        return f"Interview — {self.candidate.full_name} @ {self.scheduled_at:%Y-%m-%d}"


class Offer(TenantOwnedModel):
    """An offer extended to a candidate, with its approval lifecycle."""

    candidate = models.OneToOneField(
        Candidate, on_delete=models.CASCADE, related_name="offer"
    )
    job_title = models.CharField(max_length=160)
    salary = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    currency = models.CharField(max_length=3, default="GBP")
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    start_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=18,
        choices=OfferStatus.choices,
        default=OfferStatus.DRAFT,
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
    sent_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(
        null=True, blank=True, help_text="When the candidate accepted/declined."
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "status"])]

    def __str__(self) -> str:
        return f"Offer — {self.candidate.full_name} ({self.get_status_display()})"
