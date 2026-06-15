"""Choice enumerations for the leave / absence module (spec §9.8)."""
from django.db import models


class LeaveCategory(models.TextChoices):
    """Built-in leave categories. ``CUSTOM`` lets a tenant define its own."""

    ANNUAL = "annual", "Annual leave"
    SICK = "sick", "Sick leave"
    MATERNITY = "maternity", "Maternity leave"
    PATERNITY = "paternity", "Paternity leave"
    COMPASSIONATE = "compassionate", "Compassionate leave"
    STUDY = "study", "Study leave"
    UNPAID = "unpaid", "Unpaid leave"
    SPECIAL = "special", "Special leave"
    PUBLIC_HOLIDAY = "public_holiday", "Public holiday"
    CUSTOM = "custom", "Custom leave type"


class AccrualMethod(models.TextChoices):
    """How a leave type's yearly entitlement is granted."""

    NONE = "none", "No accrual — fixed entitlement"
    ANNUAL_LUMP = "annual_lump", "Full entitlement at start of year"
    MONTHLY = "monthly", "Accrues monthly through the year"


class GenderEligibility(models.TextChoices):
    """Restricts a leave type to a gender (e.g. maternity / paternity)."""

    ANY = "any", "Any"
    MALE = "male", "Male only"
    FEMALE = "female", "Female only"


class LeaveRequestStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    WITHDRAWN = "withdrawn", "Withdrawn"


# Statuses that reserve or consume balance.
RESERVING_STATUSES = {LeaveRequestStatus.PENDING}
CONSUMING_STATUSES = {LeaveRequestStatus.APPROVED}
# Statuses that count when checking for overlapping leave.
ACTIVE_STATUSES = {LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED}


class ApprovalStage(models.TextChoices):
    """A stage in the configurable leave-approval chain."""

    MANAGER = "manager", "Line manager approval"
    HR = "hr", "HR confirmation"
    EXTRA = "extra", "Additional approval stage"


class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    SKIPPED = "skipped", "Skipped"


class DayPortion(models.TextChoices):
    """Portion of the first/last day covered by a request (half-day support)."""

    FULL = "full", "Full day"
    FIRST_HALF = "first_half", "First half (morning)"
    SECOND_HALF = "second_half", "Second half (afternoon)"
