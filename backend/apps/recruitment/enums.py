"""Choice enumerations for the recruitment / ATS module (spec §9.5)."""
from django.db import models


class RequisitionStatus(models.TextChoices):
    """Lifecycle of a job requisition (a request to hire)."""

    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    ON_HOLD = "on_hold", "On hold"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"


class PostingStatus(models.TextChoices):
    """Lifecycle of a job posting."""

    DRAFT = "draft", "Draft"
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"
    FILLED = "filled", "Filled"


class RecruitmentStage(models.TextChoices):
    """The candidate pipeline stages (spec §9.5)."""

    APPLIED = "applied", "Applied"
    SCREENING = "screening", "Screening"
    SHORTLISTED = "shortlisted", "Shortlisted"
    INTERVIEW = "interview", "Interview"
    REFERENCE_CHECK = "reference_check", "Reference check"
    OFFER = "offer", "Offer"
    HIRED = "hired", "Hired"
    REJECTED = "rejected", "Rejected"


# Ordered pipeline used to validate forward progress.
STAGE_ORDER = [
    RecruitmentStage.APPLIED,
    RecruitmentStage.SCREENING,
    RecruitmentStage.SHORTLISTED,
    RecruitmentStage.INTERVIEW,
    RecruitmentStage.REFERENCE_CHECK,
    RecruitmentStage.OFFER,
    RecruitmentStage.HIRED,
]
# Stages where the candidate is no longer in the running.
CLOSED_STAGES = {RecruitmentStage.HIRED, RecruitmentStage.REJECTED}


class CandidateDocumentType(models.TextChoices):
    CV = "cv", "CV / résumé"
    COVER_LETTER = "cover_letter", "Cover letter"
    CERTIFICATE = "certificate", "Certificate"
    PORTFOLIO = "portfolio", "Portfolio"
    REFERENCE = "reference", "Reference"
    OTHER = "other", "Other"


class InterviewMode(models.TextChoices):
    IN_PERSON = "in_person", "In person"
    VIDEO = "video", "Video call"
    PHONE = "phone", "Phone"


class InterviewStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    NO_SHOW = "no_show", "No show"


class OfferStatus(models.TextChoices):
    """Lifecycle of an offer, including its approval step."""

    DRAFT = "draft", "Draft"
    PENDING_APPROVAL = "pending_approval", "Pending approval"
    APPROVED = "approved", "Approved"
    SENT = "sent", "Sent to candidate"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    WITHDRAWN = "withdrawn", "Withdrawn"
