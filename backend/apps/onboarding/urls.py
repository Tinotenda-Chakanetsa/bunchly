"""Onboarding / offboarding API routes."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ChecklistTaskTemplateViewSet,
    ChecklistTemplateViewSet,
    OnboardingDashboardView,
    OnboardingProgrammeViewSet,
    OnboardingTaskViewSet,
)

router = DefaultRouter()
router.register(
    "checklist-templates", ChecklistTemplateViewSet, basename="checklist-template"
)
router.register(
    "checklist-task-templates", ChecklistTaskTemplateViewSet,
    basename="checklist-task-template",
)
router.register(
    "onboarding-programmes", OnboardingProgrammeViewSet,
    basename="onboarding-programme",
)
router.register("onboarding-tasks", OnboardingTaskViewSet, basename="onboarding-task")

urlpatterns = router.urls + [
    path(
        "onboarding/dashboard/",
        OnboardingDashboardView.as_view(),
        name="onboarding-dashboard",
    ),
]
