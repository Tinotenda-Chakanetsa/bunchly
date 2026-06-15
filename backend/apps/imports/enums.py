"""Choice enumerations for the data-import module (spec §9.14)."""
from django.db import models


class ImportEntityType(models.TextChoices):
    """The entities a bulk import can populate.

    Add a new value here AND a matching definition to
    :mod:`apps.imports.entities` to extend the pipeline.
    """

    EMPLOYEES = "employees", "Employees"


class ImportStatus(models.TextChoices):
    """Lifecycle of a single import attempt."""

    DRAFT = "draft", "Draft"
    VALIDATED = "validated", "Validated"
    COMMITTED = "committed", "Committed"
    FAILED = "failed", "Failed"
