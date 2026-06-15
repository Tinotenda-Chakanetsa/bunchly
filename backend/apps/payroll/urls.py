"""Payroll API routes."""
from rest_framework.routers import DefaultRouter

from .views import (
    PayComponentViewSet,
    PayrollLineViewSet,
    PayrollPeriodViewSet,
    PayrollRecordViewSet,
    PayslipViewSet,
)

router = DefaultRouter()
router.register("payroll-periods", PayrollPeriodViewSet, basename="payroll-period")
router.register("pay-components", PayComponentViewSet, basename="pay-component")
router.register("payroll-records", PayrollRecordViewSet, basename="payroll-record")
router.register("payroll-lines", PayrollLineViewSet, basename="payroll-line")
router.register("payslips", PayslipViewSet, basename="payslip")

urlpatterns = router.urls
