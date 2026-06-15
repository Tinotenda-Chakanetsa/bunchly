"""Choice enumerations for the onboarding / offboarding module (spec §9.6, §9.7)."""
from django.db import models


class ProgrammeType(models.TextChoices):
    """Whether a programme brings an employee in or transitions them out."""

    ONBOARDING = "onboarding", "Onboarding"
    OFFBOARDING = "offboarding", "Offboarding"


class TaskOwnerRole(models.TextChoices):
    """The function responsible for a checklist task (spec §9.6)."""

    HR = "hr", "HR"
    IT = "it", "IT"
    FINANCE = "finance", "Finance"
    MANAGER = "manager", "Line manager"
    EMPLOYEE = "employee", "Employee"


class ProgrammeStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not started"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class TaskStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"
    SKIPPED = "skipped", "Skipped"
    BLOCKED = "blocked", "Blocked"


# Task statuses that count as resolved when deciding programme completion.
RESOLVED_TASK_STATUSES = {TaskStatus.COMPLETED, TaskStatus.SKIPPED}
