"""Choice enumerations for the system-settings module."""
from django.db import models


class SettingValueType(models.TextChoices):
    """How a setting's stored text value is interpreted."""

    STRING = "string", "Text"
    INTEGER = "integer", "Whole number"
    BOOLEAN = "boolean", "True / false"
    DECIMAL = "decimal", "Decimal number"
    JSON = "json", "JSON"
