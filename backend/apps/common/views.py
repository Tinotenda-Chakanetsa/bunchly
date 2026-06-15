"""Health & readiness probes for orchestrators and load balancers."""
from __future__ import annotations

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def health_check(request) -> JsonResponse:
    """Liveness probe — the process is up. No dependency checks."""
    return JsonResponse({"status": "ok", "service": "bunchly-api"})


@csrf_exempt
def readiness_check(request) -> JsonResponse:
    """Readiness probe — verifies database and cache connectivity."""
    checks: dict[str, str] = {}
    healthy = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover - infra failure path
        checks["database"] = f"error: {exc}"
        healthy = False

    try:
        cache.set("__readyz__", "1", timeout=5)
        checks["cache"] = "ok" if cache.get("__readyz__") == "1" else "error"
        healthy = healthy and checks["cache"] == "ok"
    except Exception as exc:  # pragma: no cover - infra failure path
        checks["cache"] = f"error: {exc}"
        healthy = False

    return JsonResponse(
        {"status": "ready" if healthy else "degraded", "checks": checks},
        status=200 if healthy else 503,
    )
