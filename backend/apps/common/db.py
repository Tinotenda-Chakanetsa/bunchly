"""Database helpers for the per-request tenant context used by Postgres RLS.

Every authenticated, tenant-bound HTTP request sets the
``app.tenant_id`` runtime setting on its own transaction. The matching
``bunchly_tenant_isolation`` row-level-security policy installed by
migration ``tenants/0002_enable_rls.py`` then filters every query that
touches a tenant-scoped table to the rows for that tenant — even if
application code forgets a ``.filter(tenant=...)`` clause.

The setting is scoped to the current transaction (``is_local=True``)
so Django's ``ATOMIC_REQUESTS`` automatically clears it at commit /
rollback. Connections returned to the pool never carry stale tenant
context.
"""
from __future__ import annotations

import logging

from django.db import connection

logger = logging.getLogger("bunchly.security")


def set_tenant_setting(tenant_id: str | None) -> None:
    """Set the ``app.tenant_id`` Postgres runtime setting for this txn.

    Passing ``None`` clears it so the bypass branch of the RLS policy
    applies (e.g. for platform-admin queries that legitimately span
    tenants).
    """
    if connection.vendor != "postgresql":
        # SQLite et al — RLS is a Postgres-only feature; skip silently.
        return
    try:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.tenant_id', %s, true)",
                [str(tenant_id) if tenant_id else ""],
            )
    except Exception as exc:  # noqa: BLE001
        # If the connection isn't in a transaction (rare — DRF view
        # dispatch runs inside ATOMIC_REQUESTS) just log and continue.
        logger.warning("rls.set_tenant_failed", extra={"error": str(exc)})
