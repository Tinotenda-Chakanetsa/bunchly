"""Benefits-administration API routes."""
from rest_framework.routers import DefaultRouter

from .views import BenefitTypeViewSet, EmployeeBenefitViewSet

router = DefaultRouter()
router.register("benefit-types", BenefitTypeViewSet, basename="benefit-type")
router.register("employee-benefits", EmployeeBenefitViewSet, basename="employee-benefit")

urlpatterns = router.urls
