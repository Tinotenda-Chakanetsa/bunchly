"""Education-assistance business logic (spec §9.12).

Holds the eligibility-rules engine, the claim lifecycle (submit -> HR
review -> Finance payment) and the controls that prevent duplicate or
over-limit claims. Viewsets delegate every state change here so the
rules apply uniformly and stay auditable.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.employees.enums import EmploymentStatus
from apps.notifications import services as notifications
from apps.notifications.enums import NotificationType

from .enums import (
    COUNTED_STATUSES,
    ClaimApprovalDecision,
    ClaimApprovalStage,
    ClaimStatus,
)
from .models import (
    EducationBenefitRule,
    EducationClaim,
    EducationClaimApproval,
)

ZERO = Decimal("0.00")


# --------------------------------------------------------------------------
# Rule resolution
# --------------------------------------------------------------------------
def get_active_rule(tenant) -> EducationBenefitRule | None:
    """The tenant's active education-benefit rule, if configured."""
    return EducationBenefitRule.objects.filter(tenant=tenant, is_active=True).first()


def generate_reference(tenant) -> str:
    """A per-tenant sequential claim reference (EDU-00001)."""
    count = EducationClaim.all_objects.filter(tenant=tenant).count()
    return f"EDU-{count + 1:05d}"


# --------------------------------------------------------------------------
# Eligibility & dependant controls
# --------------------------------------------------------------------------
def check_employee_eligibility(employee, rule: EducationBenefitRule) -> None:
    """Raise if the employee may not claim under the rule."""
    if rule.eligible_employment_statuses:
        if employee.employment_status not in rule.eligible_employment_statuses:
            raise ValidationError(
                "Your employment status is not eligible for this benefit."
            )
    if rule.require_probation_passed and (
        employee.employment_status == EmploymentStatus.PROBATION
    ):
        raise ValidationError(
            "Education assistance is available only after probation is passed."
        )


def eligible_dependant_count(employee, *, exclude_pk=None) -> int:
    """Number of benefit-eligible dependants registered for an employee."""
    qs = employee.dependants.filter(is_benefit_eligible=True)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs.count()


def validate_dependant_capacity(employee, rule: EducationBenefitRule, *, exclude_pk=None):
    """Block registering more benefit-eligible children than the rule allows."""
    if rule is None:
        return
    if eligible_dependant_count(employee, exclude_pk=exclude_pk) >= rule.max_children:
        raise ValidationError(
            f"This employee already has the maximum of {rule.max_children} "
            f"benefit-eligible dependant(s)."
        )


def _age(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


# --------------------------------------------------------------------------
# Claim validation
# --------------------------------------------------------------------------
def validate_claim(claim: EducationClaim, rule: EducationBenefitRule | None) -> None:
    """Apply the rule engine's controls to a claim before submission."""
    if rule is None:
        raise ValidationError(
            "Education assistance is not configured for this organisation."
        )
    check_employee_eligibility(claim.employee, rule)

    if rule.covered_levels and claim.education_level not in rule.covered_levels:
        raise ValidationError(
            {"education_level": "This education level is not covered by the policy."}
        )

    # Child age limit.
    if rule.max_child_age and claim.dependant.date_of_birth:
        age = _age(claim.dependant.date_of_birth, timezone.now().date())
        if age > rule.max_child_age:
            raise ValidationError(
                f"{claim.dependant.full_name} is above the maximum eligible "
                f"age of {rule.max_child_age}."
            )

    # Amount cap.
    if rule.max_amount_per_child and claim.amount_claimed > rule.max_amount_per_child:
        raise ValidationError(
            {"amount_claimed": f"Amount exceeds the per-child cap of "
                               f"{rule.currency} {rule.max_amount_per_child}."}
        )

    # Duplicate claim for the same child + academic period.
    duplicate = EducationClaim.objects.filter(
        tenant=claim.tenant,
        dependant=claim.dependant,
        academic_period__iexact=claim.academic_period,
        status__in=COUNTED_STATUSES,
    ).exclude(pk=claim.pk)
    if duplicate.exists():
        raise ValidationError(
            f"A claim for {claim.dependant.full_name} in "
            f"'{claim.academic_period}' already exists."
        )

    # Per-period claim count for the employee.
    period_claims = EducationClaim.objects.filter(
        tenant=claim.tenant,
        employee=claim.employee,
        academic_period__iexact=claim.academic_period,
        status__in=COUNTED_STATUSES,
    ).exclude(pk=claim.pk).count()
    if period_claims >= rule.max_claims_per_period:
        raise ValidationError(
            f"The limit of {rule.max_claims_per_period} claim(s) for "
            f"'{claim.academic_period}' has been reached."
        )

    # Required supporting documents.
    if rule.required_documents:
        present = set(claim.documents.values_list("doc_type", flat=True))
        missing = [d for d in rule.required_documents if d not in present]
        if missing:
            raise ValidationError(
                {"documents": f"Missing required documents: {', '.join(missing)}."}
            )


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
def _users_with_perm(tenant, code: str) -> list:
    """User accounts holding a permission codename within the tenant."""
    from apps.accounts.models import User

    return list(
        User.objects.filter(
            memberships__tenant=tenant,
            memberships__is_active=True,
            memberships__roles__permissions__code=code,
            is_active=True,
        ).distinct()
    )


def _claim_context(claim: EducationClaim, *, note: str = "") -> dict:
    return {
        "reference": claim.reference,
        "employee_name": claim.employee.full_name,
        "dependant_name": claim.dependant.full_name,
        "amount": f"{claim.currency} {claim.payable_amount}",
        "payment_reference": claim.payment_reference,
        "note": note,
    }


def _notify(claim, event_key, users, *, extra_emails=None, note=""):
    notifications.dispatch(
        tenant=claim.tenant,
        event_key=event_key,
        users=[u for u in users if u is not None],
        extra_emails=extra_emails or [],
        context=_claim_context(claim, note=note),
        entity_type="education_assistance.claim",
        entity_id=str(claim.pk),
    )


# --------------------------------------------------------------------------
# Claim lifecycle
# --------------------------------------------------------------------------
def submit_claim(claim: EducationClaim) -> EducationClaim:
    """Submit a draft (or more-info) claim for HR review."""
    if claim.status not in {ClaimStatus.DRAFT, ClaimStatus.MORE_INFO}:
        raise ValidationError("Only a draft claim can be submitted.")
    validate_claim(claim, get_active_rule(claim.tenant))

    claim.status = ClaimStatus.SUBMITTED
    claim.submitted_at = timezone.now()
    claim.save(update_fields=["status", "submitted_at", "updated_at"])

    _notify(
        claim,
        NotificationType.EDUCATION_CLAIM_SUBMITTED,
        _users_with_perm(claim.tenant, "education.review_claim"),
    )
    return claim


def hr_approve(claim, *, user, amount_approved=None, note: str = "") -> EducationClaim:
    """HR approves a submitted claim and routes it to Finance."""
    if claim.status not in {ClaimStatus.SUBMITTED, ClaimStatus.MORE_INFO}:
        raise ValidationError("Only a submitted claim can be approved.")
    claim.status = ClaimStatus.HR_APPROVED
    claim.amount_approved = (
        amount_approved if amount_approved is not None else claim.amount_claimed
    )
    claim.hr_reviewed_by = user
    claim.hr_reviewed_at = timezone.now()
    claim.hr_note = note[:255]
    claim.save(update_fields=[
        "status", "amount_approved", "hr_reviewed_by", "hr_reviewed_at",
        "hr_note", "updated_at",
    ])
    _record_approval(
        claim, ClaimApprovalStage.HR_REVIEW, ClaimApprovalDecision.APPROVED,
        user=user, comment=note,
    )
    _notify(
        claim, NotificationType.EDUCATION_CLAIM_APPROVED,
        [getattr(claim.employee, "user", None)],
        extra_emails=_finance_emails(claim.tenant), note=note,
    )
    return claim


def hr_reject(claim, *, user, reason: str = "") -> EducationClaim:
    """HR rejects a claim with a reason."""
    if claim.status not in {ClaimStatus.SUBMITTED, ClaimStatus.MORE_INFO}:
        raise ValidationError("Only a submitted claim can be rejected.")
    claim.status = ClaimStatus.REJECTED
    claim.hr_reviewed_by = user
    claim.hr_reviewed_at = timezone.now()
    claim.rejection_reason = reason[:255]
    claim.save(update_fields=[
        "status", "hr_reviewed_by", "hr_reviewed_at", "rejection_reason",
        "updated_at",
    ])
    _record_approval(
        claim, ClaimApprovalStage.HR_REVIEW, ClaimApprovalDecision.REJECTED,
        user=user, comment=reason,
    )
    _notify(
        claim, NotificationType.EDUCATION_CLAIM_REJECTED,
        [getattr(claim.employee, "user", None)], note=reason,
    )
    return claim


def hr_request_info(claim, *, user, note: str = "") -> EducationClaim:
    """HR sends a claim back to the employee for more information."""
    if claim.status != ClaimStatus.SUBMITTED:
        raise ValidationError("Only a submitted claim can be returned for info.")
    claim.status = ClaimStatus.MORE_INFO
    claim.hr_note = note[:255]
    claim.save(update_fields=["status", "hr_note", "updated_at"])
    _record_approval(
        claim, ClaimApprovalStage.HR_REVIEW, ClaimApprovalDecision.INFO_REQUESTED,
        user=user, comment=note,
    )
    _notify(
        claim, NotificationType.EDUCATION_CLAIM_INFO_REQUESTED,
        [getattr(claim.employee, "user", None)], note=note,
    )
    return claim


def mark_paid(claim, *, user, payment_reference: str = "", note: str = "") -> EducationClaim:
    """Finance records payment of an HR-approved claim."""
    if claim.status != ClaimStatus.HR_APPROVED:
        raise ValidationError("Only an HR-approved claim can be paid.")
    claim.status = ClaimStatus.PAID
    claim.paid_by = user
    claim.paid_at = timezone.now()
    claim.payment_reference = payment_reference[:80]
    claim.payment_note = note[:255]
    claim.save(update_fields=[
        "status", "paid_by", "paid_at", "payment_reference", "payment_note",
        "updated_at",
    ])
    _record_approval(
        claim, ClaimApprovalStage.FINANCE_PAYMENT, ClaimApprovalDecision.PAID,
        user=user, comment=note,
    )
    _notify(
        claim, NotificationType.EDUCATION_CLAIM_PAID,
        [getattr(claim.employee, "user", None)], note=note,
    )
    return claim


def cancel_claim(claim) -> EducationClaim:
    """Cancel a claim that has not yet been paid."""
    if claim.status in {ClaimStatus.PAID, ClaimStatus.CANCELLED, ClaimStatus.REJECTED}:
        raise ValidationError("This claim is already closed.")
    claim.status = ClaimStatus.CANCELLED
    claim.save(update_fields=["status", "updated_at"])
    return claim


def _record_approval(claim, stage, decision, *, user, comment="") -> EducationClaimApproval:
    return EducationClaimApproval.objects.create(
        tenant=claim.tenant,
        claim=claim,
        stage=stage,
        decision=decision,
        actor=user,
        comment=comment,
    )


def _finance_emails(tenant) -> list[str]:
    """Tenant-configured Accounts/Finance recipients (never hard-coded)."""
    tenant_settings = getattr(tenant, "settings", None)
    if tenant_settings is None:
        return []
    return list(
        (tenant_settings.notification_recipients or {}).get(
            "education_claim_approved", []
        )
    )
