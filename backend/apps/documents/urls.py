"""Document-management API routes."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .signed_urls import download_signed
from .views import DocumentCategoryViewSet, DocumentViewSet

router = DefaultRouter()
router.register("document-categories", DocumentCategoryViewSet, basename="document-category")
router.register("documents", DocumentViewSet, basename="document")

urlpatterns = router.urls + [
    # Control #9 — Secure file storage. Document files are *only* served
    # through a short-lived signed token; the storage backend itself
    # is never exposed directly.
    path("documents-download/<str:token>/", download_signed, name="document-download-signed"),
]
