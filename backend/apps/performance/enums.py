"""Choice enumerations for the performance-management module (spec §9.18)."""
from django.db import models


class ReviewCycleStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    CLOSED = "closed", "Closed"


class GoalCategory(models.TextChoices):
    """The kind of goal — objectives, KPIs and OKRs (spec §9.18)."""

    OBJECTIVE = "objective", "Objective"
    KPI = "kpi", "KPI"
    OKR = "okr", "OKR"
    DEVELOPMENT = "development", "Development"


class GoalStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not started"
    IN_PROGRESS = "in_progress", "In progress"
    ACHIEVED = "achieved", "Achieved"
    PARTIALLY_ACHIEVED = "partially_achieved", "Partially achieved"
    NOT_ACHIEVED = "not_achieved", "Not achieved"
    CANCELLED = "cancelled", "Cancelled"


class ReviewType(models.TextChoices):
    """Review perspective — manager, self and peer (360 readiness)."""

    MANAGER = "manager", "Manager review"
    SELF = "self", "Self-assessment"
    PEER = "peer", "Peer review"


class ReviewStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    COMPLETED = "completed", "Completed"


# Review statuses that are no longer editable by the reviewer.
LOCKED_REVIEW_STATUSES = {ReviewStatus.ACKNOWLEDGED, ReviewStatus.COMPLETED}


class DevelopmentPlanStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
