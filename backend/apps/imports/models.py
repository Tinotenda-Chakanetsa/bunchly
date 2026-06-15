"""Data-import models (spec §9.14).

``ImportBatch``   one attempt at a bulk import — file metadata, row totals
                  and a status lifecycle (draft → validated → committed).
``ImportError``   one row/field-level error attached to a batch. Errors are
                  collected at validate time and shown to the user so they
                  can correct the source file before committing.
"""
from __future__ import annotations

from django.db import models

from apps.common.models import BaseModel, TenantOwnedModel

from .enums import ImportEntityType, ImportStatus


class ImportBatch(TenantOwnedModel):
    """A single bulk-import attempt — validated, then committed in one go."""

    entity_type = models.CharField(
        max_length=40, choices=ImportEntityType.choices, db_index=True
    )
    status = models.CharField(
        max_length=12,
        choices=ImportStatus.choices,
        default=ImportStatus.DRAFT,
        db_index=True,
    )
    original_filename = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    committed_rows = models.PositiveIntegerField(default=0)
    committed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "entity_type"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_entity_type_display()} import — "
            f"{self.created_at:%Y-%m-%d} ({self.get_status_display()})"
        )


class ImportError(BaseModel):
    """A row/field-level error from validating an :class:`ImportBatch`.

    Scoped via its parent batch's tenant — no own ``tenant`` column needed.
    """

    batch = models.ForeignKey(
        ImportBatch, on_delete=models.CASCADE, related_name="errors"
    )
    row_number = models.PositiveIntegerField()
    field = models.CharField(max_length=80, blank=True)
    error = models.CharField(max_length=500)

    class Meta:
        ordering = ["batch", "row_number", "field"]
        indexes = [models.Index(fields=["batch", "row_number"])]

    def __str__(self) -> str:
        target = f"{self.field}: " if self.field else ""
        return f"row {self.row_number} — {target}{self.error}"
