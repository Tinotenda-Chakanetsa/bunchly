"""Choice enumerations for the learning & development module (spec §9.19)."""
from django.db import models


class CourseCategory(models.TextChoices):
    COMPLIANCE = "compliance", "Compliance"
    TECHNICAL = "technical", "Technical"
    SOFT_SKILLS = "soft_skills", "Soft skills"
    LEADERSHIP = "leadership", "Leadership"
    SAFETY = "safety", "Health & safety"
    ONBOARDING = "onboarding", "Onboarding"
    OTHER = "other", "Other"


class DeliveryMode(models.TextChoices):
    ONLINE = "online", "Online / e-learning"
    IN_PERSON = "in_person", "In person"
    BLENDED = "blended", "Blended"
    EXTERNAL = "external", "External provider"


class RecordStatus(models.TextChoices):
    """Lifecycle of an employee's training record for a course."""

    ASSIGNED = "assigned", "Assigned"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    EXPIRED = "expired", "Expired"
    CANCELLED = "cancelled", "Cancelled"


# Statuses that count as a valid, current completion for compliance.
VALID_COMPLETION_STATUSES = {RecordStatus.COMPLETED}
# Statuses where the record is still outstanding.
OPEN_RECORD_STATUSES = {RecordStatus.ASSIGNED, RecordStatus.IN_PROGRESS}


class SkillProficiency(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"
    EXPERT = "expert", "Expert"
