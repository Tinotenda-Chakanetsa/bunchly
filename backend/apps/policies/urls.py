"""Policies & Acknowledgements API routes."""
from rest_framework.routers import DefaultRouter

from .views import PolicyAssignmentViewSet, PolicyVersionViewSet, PolicyViewSet

router = DefaultRouter()
router.register("policies", PolicyViewSet, basename="policy")
router.register(
    "policy-versions", PolicyVersionViewSet, basename="policy-version"
)
router.register(
    "policy-assignments", PolicyAssignmentViewSet,
    basename="policy-assignment",
)

urlpatterns = router.urls
