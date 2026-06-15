"""Choice enumerations for the policies module (spec §9.24)."""
from django.db import models


class PolicyCategory(models.TextChoices):
    """The configurable types of policy on offer (tenant-tunable later)."""

    HR_POLICY = "hr_policy", "HR policy"
    HEALTH_SAFETY = "health_safety", "Health & safety"
    IT_ACCEPTABLE_USE = "it_acceptable_use", "IT / acceptable use"
    CODE_OF_CONDUCT = "code_of_conduct", "Code of conduct"
    PRIVACY = "privacy", "Privacy / data protection"
    COMPLIANCE = "compliance", "Regulatory / compliance"
    OTHER = "other", "Other"


class AssignmentStatus(models.TextChoices):
    """Acknowledgement status — derived but useful as a filter value."""

    PENDING = "pending", "Pending acknowledgement"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
