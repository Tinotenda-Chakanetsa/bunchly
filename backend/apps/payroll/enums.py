"""Choice enumerations for the payroll module (spec §9.10)."""
from django.db import models


class PayrollStatus(models.TextChoices):
    """Lifecycle of a payroll period."""

    DRAFT = "draft", "Draft"
    PROCESSING = "processing", "Processing"
    APPROVED = "approved", "Approved"
    PAID = "paid", "Paid"
    CLOSED = "closed", "Closed"


# Periods locked against record edits / regeneration.
LOCKED_PERIOD_STATUSES = {
    PayrollStatus.APPROVED,
    PayrollStatus.PAID,
    PayrollStatus.CLOSED,
}


class RecordStatus(models.TextChoices):
    """Lifecycle of a single employee's payroll record."""

    DRAFT = "draft", "Draft"
    APPROVED = "approved", "Approved"
    PAID = "paid", "Paid"


class ComponentType(models.TextChoices):
    """Whether a pay component adds to or subtracts from gross pay."""

    ALLOWANCE = "allowance", "Allowance"
    DEDUCTION = "deduction", "Deduction"
