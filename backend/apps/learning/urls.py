"""Learning & development API routes."""
from rest_framework.routers import DefaultRouter

from .views import (
    EmployeeSkillViewSet,
    SkillViewSet,
    TrainingCourseViewSet,
    TrainingRecordViewSet,
)

router = DefaultRouter()
router.register("training-courses", TrainingCourseViewSet, basename="training-course")
router.register("training-records", TrainingRecordViewSet, basename="training-record")
router.register("skills", SkillViewSet, basename="skill")
router.register("employee-skills", EmployeeSkillViewSet, basename="employee-skill")

urlpatterns = router.urls
