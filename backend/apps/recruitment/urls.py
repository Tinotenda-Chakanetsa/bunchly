"""Recruitment / ATS API routes."""
from rest_framework.routers import DefaultRouter

from .views import (
    CandidateDocumentViewSet,
    CandidateViewSet,
    InterviewViewSet,
    JobPostingViewSet,
    JobRequisitionViewSet,
    OfferViewSet,
)

router = DefaultRouter()
router.register("job-requisitions", JobRequisitionViewSet, basename="job-requisition")
router.register("job-postings", JobPostingViewSet, basename="job-posting")
router.register("candidates", CandidateViewSet, basename="candidate")
router.register(
    "candidate-documents", CandidateDocumentViewSet, basename="candidate-document"
)
router.register("interviews", InterviewViewSet, basename="interview")
router.register("offers", OfferViewSet, basename="offer")

urlpatterns = router.urls
