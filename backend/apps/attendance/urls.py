"""Time & attendance API routes."""
from rest_framework.routers import DefaultRouter

from .views import AttendanceRecordViewSet, ShiftViewSet, TimesheetViewSet

router = DefaultRouter()
router.register("shifts", ShiftViewSet, basename="shift")
router.register(
    "attendance-records", AttendanceRecordViewSet, basename="attendance-record"
)
router.register("timesheets", TimesheetViewSet, basename="timesheet")

urlpatterns = router.urls
