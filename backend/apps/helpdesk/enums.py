"""Choice enumerations for the HR helpdesk / case-management module (spec §9.22)."""
from django.db import models


class CasePriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class CaseStatus(models.TextChoices):
    """Lifecycle of an HR case."""

    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In progress"
    ON_HOLD = "on_hold", "On hold"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"


# Statuses where the case is still being worked.
OPEN_CASE_STATUSES = {
    CaseStatus.OPEN,
    CaseStatus.IN_PROGRESS,
    CaseStatus.ON_HOLD,
}
# Statuses where the case is finished.
CLOSED_CASE_STATUSES = {
    CaseStatus.RESOLVED,
    CaseStatus.CLOSED,
    CaseStatus.CANCELLED,
}
