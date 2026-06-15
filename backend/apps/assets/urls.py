"""Asset-management API routes."""
from rest_framework.routers import DefaultRouter

from .views import AssetAssignmentViewSet, AssetCategoryViewSet, AssetViewSet

router = DefaultRouter()
router.register("asset-categories", AssetCategoryViewSet, basename="asset-category")
router.register("assets", AssetViewSet, basename="asset")
router.register(
    "asset-assignments", AssetAssignmentViewSet, basename="asset-assignment"
)

urlpatterns = router.urls
