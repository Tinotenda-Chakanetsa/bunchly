"""Employees / core-HR API routes."""
from rest_framework.routers import DefaultRouter

from .views import (
    ContractTemplateViewSet,
    EmployeeHistoryViewSet,
    EmployeeViewSet,
    EmergencyContactViewSet,
    EmploymentContractViewSet,
)

router = DefaultRouter()
router.register("employees", EmployeeViewSet, basename="employee")
router.register("emergency-contacts", EmergencyContactViewSet, basename="emergency-contact")
router.register("contracts", EmploymentContractViewSet, basename="contract")
router.register(
    "contract-templates", ContractTemplateViewSet, basename="contract-template"
)
router.register("history", EmployeeHistoryViewSet, basename="employee-history")

urlpatterns = router.urls
