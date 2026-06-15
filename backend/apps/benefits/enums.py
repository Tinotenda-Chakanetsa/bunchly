"""Choice enumerations for the benefits-administration module (spec §9.11)."""
from django.db import models


class BenefitCategory(models.TextChoices):
    HEALTH = "health", "Health / medical"
    DENTAL = "dental", "Dental"
    VISION = "vision", "Vision"
    LIFE_INSURANCE = "life_insurance", "Life insurance"
    DISABILITY = "disability", "Disability cover"
    PENSION = "pension", "Pension / retirement"
    WELLNESS = "wellness", "Wellness"
    TRANSPORT = "transport", "Transport"
    HOUSING = "housing", "Housing"
    OTHER = "other", "Other"


class ContributionBasis(models.TextChoices):
    """How a benefit contribution amount is interpreted."""

    FIXED = "fixed", "Fixed amount per period"
    PERCENTAGE = "percentage", "Percentage of basic salary"


class EnrolmentStatus(models.TextChoices):
    """Lifecycle of an employee's enrolment in a benefit."""

    PENDING = "pending", "Pending approval"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    DECLINED = "declined", "Declined"
    TERMINATED = "terminated", "Terminated"


# Enrolments that count as currently in force (for deductions / reports).
IN_FORCE_STATUSES = {EnrolmentStatus.ACTIVE}


class EnrolmentEvent(models.TextChoices):
    """An entry in an enrolment's history log."""

    ENROLLED = "enrolled", "Enrolled"
    APPROVED = "approved", "Approved"
    DECLINED = "declined", "Declined"
    SUSPENDED = "suspended", "Suspended"
    RESUMED = "resumed", "Resumed"
    TERMINATED = "terminated", "Terminated"
    UPDATED = "updated", "Updated"
