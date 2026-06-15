"""Reports module models (spec §9.17).

The module is read-only over the rest of the system; the only stored
state is ``SavedReport`` — a saved report definition (key + filters) so
users can re-run a configured report ("saveable as report templates").
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import ReportKey


class SavedReport(TenantOwnedModel):
    """A saved report configuration a user can re-run.

    ``filters`` stores the date range / department / other parameters the
    report was configured with. ``is_shared`` exposes it to other users
    holding ``reports.view`` in the tenant.
    """

    name = models.CharField(max_length=160)
    report_key = models.CharField(max_length=40, choices=ReportKey.choices)
    description = models.TextField(blank=True)
    filters = models.JSONField(
        default=dict, blank=True, help_text="Saved filter parameters."
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_reports",
    )
    is_shared = models.BooleanField(
        default=False, help_text="Visible to other report users in the tenant."
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "owner"]),
            models.Index(fields=["tenant", "report_key"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.report_key})"
