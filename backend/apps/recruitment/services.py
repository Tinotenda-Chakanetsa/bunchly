"""Recruitment business logic (spec §9.5).

Covers the candidate pipeline, the offer lifecycle and conversion of a
hired candidate into an ``Employee`` record. Viewsets delegate every
state change here so stage / status rules apply uniformly.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.employees.enums import EmploymentStatus
from apps.employees.models import Employee

from .enums import (
    CLOSED_STAGES,
    OfferStatus,
    RecruitmentStage,
    STAGE_ORDER,
)
from .models import Candidate, JobRequisition, Offer


# --------------------------------------------------------------------------
# References
# --------------------------------------------------------------------------
def generate_requisition_reference(tenant) -> str:
    """A per-tenant sequential requisition reference (REQ-00001)."""
    count = JobRequisition.all_objects.filter(tenant=tenant).count()
    return f"REQ-{count + 1:05d}"


def _next_employee_number(tenant) -> str:
    """A free, sequential employee number for a converted candidate."""
    count = Employee.all_objects.filter(tenant=tenant).count()
    while True:
        count += 1
        number = f"EMP-{count:04d}"
        if not Employee.all_objects.filter(
            tenant=tenant, employee_number=number
        ).exists():
            return number


# --------------------------------------------------------------------------
# Candidate pipeline
# --------------------------------------------------------------------------
def advance_candidate(candidate: Candidate, stage: str) -> Candidate:
    """Move a candidate to a new pipeline stage.

    Forward moves through the ordered pipeline are allowed, as is a jump
    to ``rejected``. Backwards moves and changes on a closed candidate
    are refused.
    """
    if candidate.stage in CLOSED_STAGES:
        raise ValidationError(
            f"This candidate is already {candidate.get_stage_display().lower()}."
        )
    if stage == RecruitmentStage.REJECTED:
        return reject_candidate(candidate, reason="")
    if stage not in STAGE_ORDER:
        raise ValidationError({"stage": f"Cannot move to stage '{stage}'."})
    if STAGE_ORDER.index(stage) < STAGE_ORDER.index(candidate.stage):
        raise ValidationError(
            {"stage": "A candidate cannot be moved backwards in the pipeline."}
        )
    candidate.stage = stage
    candidate.save(update_fields=["stage", "updated_at"])
    return candidate


def reject_candidate(candidate: Candidate, *, reason: str = "") -> Candidate:
    """Reject a candidate, recording the reason."""
    if candidate.stage in CLOSED_STAGES:
        raise ValidationError("This candidate's application is already closed.")
    candidate.stage = RecruitmentStage.REJECTED
    candidate.rejection_reason = reason[:255]
    candidate.save(update_fields=["stage", "rejection_reason", "updated_at"])
    return candidate


# --------------------------------------------------------------------------
# Offer lifecycle
# --------------------------------------------------------------------------
def submit_offer(offer: Offer) -> Offer:
    """Submit a draft offer for approval."""
    if offer.status != OfferStatus.DRAFT:
        raise ValidationError("Only a draft offer can be submitted for approval.")
    offer.status = OfferStatus.PENDING_APPROVAL
    offer.save(update_fields=["status", "updated_at"])
    return offer


def approve_offer(offer: Offer, *, user) -> Offer:
    """Approve an offer that is pending approval."""
    if offer.status != OfferStatus.PENDING_APPROVAL:
        raise ValidationError("Only an offer pending approval can be approved.")
    offer.status = OfferStatus.APPROVED
    offer.approved_by = user
    offer.approved_at = timezone.now()
    offer.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    return offer


def send_offer(offer: Offer) -> Offer:
    """Mark an approved offer as sent to the candidate."""
    if offer.status != OfferStatus.APPROVED:
        raise ValidationError("Only an approved offer can be sent.")
    offer.status = OfferStatus.SENT
    offer.sent_at = timezone.now()
    offer.save(update_fields=["status", "sent_at", "updated_at"])
    # Move the candidate into the offer stage if not already past it.
    candidate = offer.candidate
    if candidate.stage not in CLOSED_STAGES and candidate.stage != RecruitmentStage.OFFER:
        candidate.stage = RecruitmentStage.OFFER
        candidate.save(update_fields=["stage", "updated_at"])
    return offer


def accept_offer(offer: Offer) -> Offer:
    """Record candidate acceptance — the candidate becomes hired."""
    if offer.status != OfferStatus.SENT:
        raise ValidationError("Only a sent offer can be accepted.")
    offer.status = OfferStatus.ACCEPTED
    offer.decided_at = timezone.now()
    offer.save(update_fields=["status", "decided_at", "updated_at"])
    candidate = offer.candidate
    candidate.stage = RecruitmentStage.HIRED
    candidate.save(update_fields=["stage", "updated_at"])
    return offer


def decline_offer(offer: Offer) -> Offer:
    """Record candidate declining a sent offer."""
    if offer.status != OfferStatus.SENT:
        raise ValidationError("Only a sent offer can be declined.")
    offer.status = OfferStatus.DECLINED
    offer.decided_at = timezone.now()
    offer.save(update_fields=["status", "decided_at", "updated_at"])
    return offer


def withdraw_offer(offer: Offer) -> Offer:
    """Withdraw an offer before it is accepted or declined."""
    if offer.status in {
        OfferStatus.ACCEPTED, OfferStatus.DECLINED, OfferStatus.WITHDRAWN,
    }:
        raise ValidationError("This offer is already closed.")
    offer.status = OfferStatus.WITHDRAWN
    offer.save(update_fields=["status", "updated_at"])
    return offer


# --------------------------------------------------------------------------
# Convert to employee
# --------------------------------------------------------------------------
@transaction.atomic
def convert_to_employee(candidate: Candidate, *, user=None) -> Employee:
    """Create an ``Employee`` record from a hired candidate.

    The requisition behind the posting supplies the organisational
    placement; an accepted offer supplies start date and employment type.
    """
    if candidate.linked_employee_id is not None:
        raise ValidationError("This candidate has already been converted.")
    if candidate.stage != RecruitmentStage.HIRED:
        raise ValidationError("Only a hired candidate can be converted to an employee.")

    requisition = getattr(candidate.posting, "requisition", None)
    offer = getattr(candidate, "offer", None)

    employee = Employee.objects.create(
        tenant=candidate.tenant,
        employee_number=_next_employee_number(candidate.tenant),
        first_name=candidate.first_name,
        last_name=candidate.last_name,
        personal_email=candidate.email,
        phone=candidate.phone,
        department=getattr(requisition, "department", None),
        job_title=getattr(requisition, "job_title", None),
        grade=getattr(requisition, "grade", None),
        employment_type=(
            offer.employment_type if offer else candidate.posting.employment_type
        ),
        employment_status=EmploymentStatus.PROBATION,
        start_date=offer.start_date if offer else None,
        current_salary=offer.salary if offer else None,
        salary_currency=offer.currency if offer else "GBP",
    )
    candidate.linked_employee = employee
    candidate.save(update_fields=["linked_employee", "updated_at"])
    return employee
