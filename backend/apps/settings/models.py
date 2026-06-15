"""System-settings model.

``SystemSetting`` is a per-tenant, typed key/value store for operational
configuration that does not belong to a specific domain module. The raw
value is stored as text and cast on read per ``value_type`` (see
``services.cast_value``).
"""
from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import SettingValueType


class SystemSetting(TenantOwnedModel):
    """A single per-tenant configuration value."""

    key = models.CharField(max_length=120, db_index=True)
    group = models.CharField(max_length=60, blank=True, db_index=True)
    label = models.CharField(max_length=160, blank=True)
    description = models.CharField(max_length=255, blank=True)
    value_type = models.CharField(
        max_length=10,
        choices=SettingValueType.choices,
        default=SettingValueType.STRING,
    )
    value = models.TextField(blank=True, help_text="Raw value; cast per value_type.")
    is_public = models.BooleanField(
        default=False,
        help_text="Readable by any tenant member; otherwise admin-only.",
    )
    is_editable = models.BooleanField(
        default=True, help_text="A locked setting cannot be changed via the API."
    )

    class Meta:
        ordering = ["group", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "key"], name="uniq_systemsetting_key_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "group"])]

    def __str__(self) -> str:
        return f"{self.key} = {self.value}"
