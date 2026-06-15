"""HR helpdesk / case-management API routes."""
from rest_framework.routers import DefaultRouter

from .views import (
    CaseAttachmentViewSet,
    CaseCategoryViewSet,
    CaseCommentViewSet,
    HRCaseViewSet,
)

router = DefaultRouter()
router.register("case-categories", CaseCategoryViewSet, basename="case-category")
router.register("hr-cases", HRCaseViewSet, basename="hr-case")
router.register("case-comments", CaseCommentViewSet, basename="case-comment")
router.register("case-attachments", CaseAttachmentViewSet, basename="case-attachment")

urlpatterns = router.urls
