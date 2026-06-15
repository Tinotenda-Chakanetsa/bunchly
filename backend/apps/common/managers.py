"""Reusable managers and querysets: soft-delete + tenant scoping."""
from __future__ import annotations

from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that treats ``delete()`` as a soft delete."""

    def alive(self) -> "SoftDeleteQuerySet":
        return self.filter(is_deleted=False)

    def dead(self) -> "SoftDeleteQuerySet":
        return self.filter(is_deleted=True)

    def for_tenant(self, tenant) -> "SoftDeleteQuerySet":
        """Scope the queryset to a single tenant.

        Accepts a Tenant instance or a tenant id. Passing ``None`` returns
        an empty queryset — fail closed rather than leaking data.
        """
        if tenant is None:
            return self.none()
        return self.filter(tenant=tenant)

    def delete(self):  # type: ignore[override]
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()


class SoftDeleteManager(models.Manager):
    """Default manager — hides soft-deleted rows."""

    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

    def for_tenant(self, tenant) -> SoftDeleteQuerySet:
        return self.get_queryset().for_tenant(tenant)


class AllObjectsManager(models.Manager):
    """Escape-hatch manager that includes soft-deleted rows."""

    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db)
