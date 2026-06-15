"""Request-scoped middleware: request context + tenant resolution + monitor."""
from __future__ import annotations

import logging
import time
import uuid

from django.conf import settings
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

from .context import RequestContext, clear_context, get_context, set_context

logger = logging.getLogger("bunchly.request")
security_logger = logging.getLogger("bunchly.security")

REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"
TENANT_HEADER = "HTTP_X_TENANT"


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class RequestContextMiddleware(MiddlewareMixin):
    """Assigns a request id, builds the request context, logs the request.

    Structured access logs carry request id, user id, tenant id, IP,
    user agent, endpoint, status and latency — never request bodies, so
    no secrets/PII are logged here.
    """

    def process_request(self, request) -> None:
        request_id = request.META.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        ctx = RequestContext(
            request_id=request_id,
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
        )
        set_context(ctx)
        request.request_id = request_id
        request._bunchly_start = time.monotonic()

    def process_response(self, request, response):
        ctx = get_context()
        # request.user is reliable for session auth; DRF JWT auth also
        # refreshes ctx.user, so prefer the context value.
        latency_ms = None
        start = getattr(request, "_bunchly_start", None)
        if start is not None:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
        response["X-Request-ID"] = ctx.request_id
        logger.info(
            "request",
            extra={
                "request_id": ctx.request_id,
                "user_id": str(ctx.user_id) if ctx.user_id else None,
                "tenant_id": str(ctx.tenant_id) if ctx.tenant_id else None,
                "ip_address": ctx.ip_address,
                "user_agent": ctx.user_agent,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        clear_context()
        return response

    def process_exception(self, request, exception) -> None:
        ctx = get_context()
        logger.error(
            "request.exception",
            extra={
                "request_id": ctx.request_id,
                "user_id": str(ctx.user_id) if ctx.user_id else None,
                "tenant_id": str(ctx.tenant_id) if ctx.tenant_id else None,
                "path": request.path,
                "error": str(exception),
            },
        )


class TenantMiddleware(MiddlewareMixin):
    """Resolves a *candidate* tenant from subdomain or ``X-Tenant`` header.

    This runs before authentication, so it can only produce a hint. The
    authoritative tenant for an authenticated API request is set by
    ``TenantJWTAuthentication`` from the verified token claim, which also
    cross-checks this hint to reject mismatches.
    """

    def process_request(self, request) -> None:
        request.tenant = None
        request.tenant_hint = None

        hint = request.META.get(TENANT_HEADER)
        if not hint:
            host = request.get_host().split(":")[0]
            labels = host.split(".")
            # tenant.bunchly.com -> "tenant"; ignore bare domains / IPs.
            if len(labels) >= 3 and labels[0] not in ("www", "app", "api"):
                hint = labels[0]

        if not hint:
            return

        tenant = self._lookup(hint)
        request.tenant_hint = tenant
        get_context().tenant = tenant

    @staticmethod
    def _lookup(hint: str):
        """Look up a tenant by slug or domain. Returns None if not found."""
        try:
            from apps.tenants.models import Tenant, TenantDomain
        except Exception:  # apps not ready / not migrated
            return None
        tenant = (
            Tenant.objects.filter(slug=hint, is_active=True).first()
        )
        if tenant is not None:
            return tenant
        domain = (
            TenantDomain.objects.select_related("tenant")
            .filter(domain=hint, tenant__is_active=True)
            .first()
        )
        return domain.tenant if domain else None


# Control #14 — Security monitoring.
#
# This middleware looks for two suspicious patterns on every request:
#
# 1. **Cross-tenant attempts** — the X-Tenant header says one tenant
#    but the JWT was issued for a different tenant. Caught earlier by
#    ``TenantJWTAuthentication`` (raises 401), but logging it here lets
#    SecOps see repeated probing.
#
# 2. **Bulk exports** — N+ export/download responses from the same
#    user within a rolling window. Threshold + window are configurable
#    via ``SECURITY_BULK_EXPORT_THRESHOLD`` /
#    ``SECURITY_BULK_EXPORT_WINDOW_SECONDS`` env vars.
#
# Hits are written to the structured ``bunchly.security`` logger so they
# show up in the SIEM next to the regular request log; they don't block
# the request — that's a deliberate detect-then-respond posture.
EXPORT_PATH_HINTS = ("/export", "/download", "/contracts/", "/payslips")


class SecurityMonitorMiddleware(MiddlewareMixin):
    def process_request(self, request) -> None:
        # Cross-tenant probe: header tenant != JWT tenant. The JWT auth
        # runs later; record the hint here so we can correlate failures.
        hint = getattr(request, "tenant_hint", None)
        if hint is not None:
            request._bunchly_hint_id = hint.id

    def process_response(self, request, response):
        ctx = get_context()
        user_id = ctx.user_id

        # Bulk-export tracking — only count successful downloads.
        if user_id and 200 <= response.status_code < 300 and any(
            seg in request.path for seg in EXPORT_PATH_HINTS
        ):
            key = f"bunchly:sec:exports:{user_id}"
            count = cache.get(key, 0) + 1
            window = settings.SECURITY_BULK_EXPORT_WINDOW_SECONDS
            cache.set(key, count, timeout=window)
            threshold = settings.SECURITY_BULK_EXPORT_THRESHOLD
            if count >= threshold:
                security_logger.warning(
                    "security.bulk_export",
                    extra={
                        "user_id": str(user_id),
                        "tenant_id": str(ctx.tenant_id) if ctx.tenant_id else None,
                        "path": request.path,
                        "count_in_window": count,
                        "window_seconds": window,
                        "threshold": threshold,
                    },
                )

        # Cross-tenant probe correlation — if the JWT auth rejected the
        # request with 401 and the hint disagreed with the token tenant,
        # log it so a SIEM can spot brute-force tenant guessing.
        hint_id = getattr(request, "_bunchly_hint_id", None)
        if (
            hint_id is not None
            and ctx.tenant_id is not None
            and str(hint_id) != str(ctx.tenant_id)
        ):
            security_logger.warning(
                "security.cross_tenant_hint_mismatch",
                extra={
                    "user_id": str(user_id) if user_id else None,
                    "hint_tenant_id": str(hint_id),
                    "jwt_tenant_id": str(ctx.tenant_id),
                    "path": request.path,
                    "ip_address": ctx.ip_address,
                },
            )

        return response
