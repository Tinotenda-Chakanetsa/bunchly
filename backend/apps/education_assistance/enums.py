"""Choice enumerations for the education-assistance module (spec §9.12)."""
from django.db import models


class EducationLevel(models.TextChoices):
    PRIMARY = "primary", "Primary"
    SECONDARY = "secondary", "Secondary"
    TERTIARY = "tertiary", "Tertiary"


class AcademicPeriodType(models.TextChoices):
    """The cadence a claim / benefit rule is measured against."""

    TERM = "term", "Per term"
    SEMESTER = "semester", "Per semester"
    YEAR = "year", "Per year"


class DependantRelationship(models.TextChoices):
    CHILD = "child", "Child"
    STEPCHILD = "stepchild", "Stepchild"
    WARD = "ward", "Ward"
    OTHER = "other", "Other"


class ClaimStatus(models.TextChoices):
    """Lifecycle of an education-assistance claim (spec §9.12 D)."""

    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted — pending HR review"
    MORE_INFO = "more_info", "More information required"
    HR_APPROVED = "hr_approved", "HR approved — pending payment"
    REJECTED = "rejected", "Rejected"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"


# Statuses that count towards per-period / cumulative limits.
COUNTED_STATUSES = {
    ClaimStatus.SUBMITTED,
    ClaimStatus.MORE_INFO,
    ClaimStatus.HR_APPROVED,
    ClaimStatus.PAID,
}
# Statuses where the claim is finished.
CLOSED_STATUSES = {ClaimStatus.REJECTED, ClaimStatus.PAID, ClaimStatus.CANCELLED}


class ClaimApprovalStage(models.TextChoices):
    HR_REVIEW = "hr_review", "HR review"
    FINANCE_PAYMENT = "finance_payment", "Finance payment"


class ClaimApprovalDecision(models.TextChoices):
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    INFO_REQUESTED = "info_requested", "More information requested"
    PAID = "paid", "Paid"


class ClaimDocumentType(models.TextChoices):
    INVOICE = "invoice", "Invoice / receipt"
    PROOF_OF_REGISTRATION = "proof_of_registration", "Proof of registration"
    BIRTH_CERTIFICATE = "birth_certificate", "Birth certificate"
    PROOF_OF_PAYMENT = "proof_of_payment", "Proof of payment"
    OTHER = "other", "Other"
