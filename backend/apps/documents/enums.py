"""Choice enumerations for the document-management module (spec §9.13)."""
from django.db import models


class DocumentStatus(models.TextChoices):
    """Lifecycle of an employee document."""

    PENDING = "pending", "Pending approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"
    ARCHIVED = "archived", "Archived"


# Statuses that mean the document is in force / countable for compliance.
VALID_STATUSES = {DocumentStatus.APPROVED}
