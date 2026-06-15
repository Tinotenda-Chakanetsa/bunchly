"""Performance-management API routes."""
from rest_framework.routers import DefaultRouter

from .views import (
    DevelopmentPlanViewSet,
    GoalViewSet,
    PerformanceReviewViewSet,
    ReviewCycleViewSet,
    ReviewItemViewSet,
)

router = DefaultRouter()
router.register("review-cycles", ReviewCycleViewSet, basename="review-cycle")
router.register("goals", GoalViewSet, basename="goal")
router.register(
    "performance-reviews", PerformanceReviewViewSet, basename="performance-review"
)
router.register("review-items", ReviewItemViewSet, basename="review-item")
router.register(
    "development-plans", DevelopmentPlanViewSet, basename="development-plan"
)

urlpatterns = router.urls
