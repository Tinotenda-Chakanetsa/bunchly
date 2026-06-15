"""Abstract base models shared across every Bunchly module.

Layering:
    UUIDModel          -> UUID primary key
    TimeStampedModel   -> created_at / updated_at
    ActorStampedModel  -> created_by / updated_by
    SoftDeleteModel    -> is_deleted / deleted_at (+ soft-delete managers)
    BaseModel          -> UUID + timestamps + actors
    TenantOwnedModel   -> BaseModel + soft delete + tenant FK

Every tenant-owned domain model should subclass ``TenantOwnedModel`` so
that tenant isolation, auditing hooks and soft deletes are uniform.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from .managers import AllObjectsManager, SoftDeleteManager


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class ActorStampedModel(models.Model):
    """Tracks which user created/updated a row.

    ``created_by``/``updated_by`` are populated automatically from the
    request context by ``TenantOwnedModel.save`` when available.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, hard=False):
        """Soft delete by default; pass ``hard=True`` to remove the row."""
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
        return None

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])


class BaseModel(UUIDModel, TimeStampedModel, ActorStampedModel):
    class Meta:
        abstract = True


class TenantOwnedModel(BaseModel, SoftDeleteModel):
    """Base for every model that belongs to a tenant.

    Carries the ``tenant`` foreign key (indexed) and auto-fills actor
    fields from the request context. Tenant isolation itself is enforced
    by viewset querysets / permission classes — this just guarantees the
    column and index exist everywhere.
    """

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        db_index=True,
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from .context import get_current_user

        user = get_current_user()
        if user is not None and getattr(user, "is_authenticated", False):
            if self._state.adding and self.created_by_id is None:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)
