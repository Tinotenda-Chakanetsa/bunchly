"""Workflow-engine API routes."""
from rest_framework.routers import DefaultRouter

from .views import WorkflowInstanceViewSet, WorkflowStageViewSet, WorkflowViewSet

router = DefaultRouter()
router.register("workflows", WorkflowViewSet, basename="workflow")
router.register("workflow-stages", WorkflowStageViewSet, basename="workflow-stage")
router.register(
    "workflow-instances", WorkflowInstanceViewSet, basename="workflow-instance"
)

urlpatterns = router.urls
