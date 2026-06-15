"""Tenant API routes."""
from rest_framework.routers import DefaultRouter

from .views import CurrentTenantViewSet, TenantViewSet

router = DefaultRouter()
router.register("organisations", TenantViewSet, basename="tenant")
router.register("current", CurrentTenantViewSet, basename="current-tenant")

urlpatterns = router.urls
