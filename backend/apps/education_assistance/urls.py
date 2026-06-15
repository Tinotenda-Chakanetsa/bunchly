"""Education-assistance API routes."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DependantViewSet,
    EducationBenefitRuleViewSet,
    EducationClaimApprovalViewSet,
    EducationClaimDocumentViewSet,
    EducationClaimViewSet,
    EducationDashboardView,
)

router = DefaultRouter()
router.register("education-benefit-rules", EducationBenefitRuleViewSet, basename="education-rule")
router.register("dependants", DependantViewSet, basename="dependant")
router.register("education-claims", EducationClaimViewSet, basename="education-claim")
router.register(
    "education-claim-documents", EducationClaimDocumentViewSet,
    basename="education-claim-document",
)
router.register(
    "education-claim-approvals", EducationClaimApprovalViewSet,
    basename="education-claim-approval",
)

urlpatterns = router.urls + [
    path(
        "education-assistance/dashboard/",
        EducationDashboardView.as_view(),
        name="education-dashboard",
    ),
]
