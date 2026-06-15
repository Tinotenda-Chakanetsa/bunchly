"""System-settings API routes."""
from rest_framework.routers import DefaultRouter

from .views import SystemSettingViewSet

router = DefaultRouter()
router.register("system-settings", SystemSettingViewSet, basename="system-setting")

urlpatterns = router.urls
