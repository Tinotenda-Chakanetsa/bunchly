"""Root URL configuration for Bunchly."""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.common.views import health_check, readiness_check

api_v1 = [
    path("auth/", include("apps.accounts.urls")),
    path("tenants/", include("apps.tenants.urls")),
    path("audit/", include("apps.audit.urls")),
    path("organisation/", include("apps.organisation.urls")),
    path("", include("apps.employees.urls")),
    path("", include("apps.leave.urls")),
    path("", include("apps.documents.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.workflows.urls")),
    path("", include("apps.reports.urls")),
    path("", include("apps.education_assistance.urls")),
    path("", include("apps.payroll.urls")),
    path("", include("apps.benefits.urls")),
    path("", include("apps.recruitment.urls")),
    path("", include("apps.onboarding.urls")),
    path("", include("apps.performance.urls")),
    path("", include("apps.learning.urls")),
    path("", include("apps.assets.urls")),
    path("", include("apps.helpdesk.urls")),
    path("", include("apps.attendance.urls")),
    path("", include("apps.imports.urls")),
    path("", include("apps.policies.urls")),
    path("", include("apps.settings.urls")),
    # Domain module routers are mounted here as modules are built.
]

urlpatterns = [
    path("admin/", admin.site.urls),
    # Health & readiness probes (for orchestrators / load balancers).
    path("healthz/", health_check, name="health-check"),
    path("readyz/", readiness_check, name="readiness-check"),
    # Public-facing health endpoint surfaced through the Tailscale funnel
    # mount at /api/. Mirrors /healthz/ so the funnel URL doesn't need to
    # know the internal Django route name.
    path("api/health/", health_check, name="health-check-public"),
    # API
    path("api/v1/", include((api_v1, "api"), namespace="v1")),
    # OpenAPI schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
