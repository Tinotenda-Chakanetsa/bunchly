"""Choice enumerations for the asset-management module (spec §9.23)."""
from django.db import models


class AssetStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    ASSIGNED = "assigned", "Assigned"
    IN_REPAIR = "in_repair", "In repair"
    LOST = "lost", "Lost / stolen"
    RETIRED = "retired", "Retired / disposed"


class AssetCondition(models.TextChoices):
    NEW = "new", "New"
    GOOD = "good", "Good"
    FAIR = "fair", "Fair"
    POOR = "poor", "Poor"
    DAMAGED = "damaged", "Damaged"


class AssignmentStatus(models.TextChoices):
    """Lifecycle of an asset assignment."""

    ISSUED = "issued", "Issued"
    RETURNED = "returned", "Returned"
    LOST = "lost", "Lost while assigned"


# An asset is free to re-issue only when it is available.
ASSIGNABLE_STATUSES = {AssetStatus.AVAILABLE}
