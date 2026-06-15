"""Reports & analytics API routes."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DashboardView,
    ReportCatalogueView,
    ReportExportView,
    ReportRunView,
    SavedReportViewSet,
)

router = DefaultRouter()
router.register("saved-reports", SavedReportViewSet, basename="saved-report")

urlpatterns = router.urls + [
    path("reports/catalogue/", ReportCatalogueView.as_view(), name="report-catalogue"),
    path("reports/run/", ReportRunView.as_view(), name="report-run"),
    path("reports/export/", ReportExportView.as_view(), name="report-export"),
    path("reports/dashboard/", DashboardView.as_view(), name="report-dashboard"),
]
