"""Organisation-structure API routes."""
from rest_framework.routers import DefaultRouter

from .views import (
    CostCentreViewSet,
    DepartmentViewSet,
    GradeViewSet,
    JobTitleViewSet,
    LocationViewSet,
    PositionViewSet,
    TeamViewSet,
)

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("teams", TeamViewSet, basename="team")
router.register("locations", LocationViewSet, basename="location")
router.register("job-titles", JobTitleViewSet, basename="job-title")
router.register("grades", GradeViewSet, basename="grade")
router.register("cost-centres", CostCentreViewSet, basename="cost-centre")
router.register("positions", PositionViewSet, basename="position")

urlpatterns = router.urls
