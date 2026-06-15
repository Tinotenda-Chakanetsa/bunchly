"""Leave & absence API routes."""
from rest_framework.routers import DefaultRouter

from .views import (
    LeaveApprovalViewSet,
    LeaveBalanceViewSet,
    LeaveRequestViewSet,
    LeaveTypeViewSet,
)

router = DefaultRouter()
router.register("leave-types", LeaveTypeViewSet, basename="leave-type")
router.register("leave-balances", LeaveBalanceViewSet, basename="leave-balance")
router.register("leave-requests", LeaveRequestViewSet, basename="leave-request")
router.register("leave-approvals", LeaveApprovalViewSet, basename="leave-approval")

urlpatterns = router.urls
