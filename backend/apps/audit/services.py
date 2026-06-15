"""Audit-recording service.

``record_audit`` is the single entry point modules call to write an
audit entry. It pulls actor / tenant / request metadata from the request
context so callers only supply what is specific to the action.
"""
from __future__ import annotations

import logging
from typing import Any

from apps.common.context import get_context

from .models import AuditLog

logger = logging.getLogger("bunchly.audit")

# Keys whose values must never be persisted to the audit trail.
SENSITIVE_KEYS = {
    "password", "token", "salary", "bank_account", "bank_details",
    "national_id", "passport_number", "tax_id", "ssn",
}


def redact(data: dict[str, Any] | None) -> dict[str, Any]:
    """Mask sensitive values in a change dict before persistence."""
    if not data:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if any(s in key.lower() for s in SENSITIVE_KEYS):
            cleaned[key] = "***redacted***"
        elif isinstance(value, dict):
            cleaned[key] = redact(value)
        else:
            cleaned[key] = value
    return cleaned


def record_audit(
    action: str,
    entity_type: str,
    *,
    entity_id: str | int | None = None,
    description: str = "",
    before: dict | None = None,
    after: dict | None = None,
    reason: str = "",
    tenant=None,
    actor=None,
) -> AuditLog | None:
    """Write one audit entry. Never raises — auditing must not break a request."""
    try:
        ctx = get_context()
        tenant = tenant or ctx.tenant
        actor = actor or (ctx.user if getattr(ctx.user, "is_authenticated", False) else None)

        changes: dict[str, Any] = {}
        if before is not None:
            changes["before"] = redact(before)
        if after is not None:
            changes["after"] = redact(after)

        entry = AuditLog.objects.create(
            tenant=tenant,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id="" if entity_id is None else str(entity_id),
            description=description[:255],
            changes=changes,
            reason=reason,
            request_id=ctx.request_id,
            ip_address=ctx.ip_address,
            user_agent=ctx.user_agent,
        )
        logger.info(
            "audit",
            extra={
                "audit_action": action,
                "entity_type": entity_type,
                "entity_id": str(entity_id) if entity_id else None,
                "tenant_id": str(tenant.id) if tenant else None,
                "request_id": ctx.request_id,
            },
        )
        return entry
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to record audit entry")
        return None
