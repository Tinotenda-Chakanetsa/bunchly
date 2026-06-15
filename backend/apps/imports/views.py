"""Viewsets for the data-import module (spec §9.14).

Two-step workflow: ``POST /imports/validate/`` parses and validates a
file (returns a batch + every error), then ``POST /imports/{id}/commit/``
re-validates the same file and creates rows for every clean entry. The
template endpoint returns a header-only CSV the user can fill in.
"""
from __future__ import annotations

from django.http import HttpResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.mixins import TenantScopedViewSetMixin
from apps.common.permissions import HasModulePermission, HasTenant

from . import services
from .enums import ImportEntityType
from .models import ImportBatch
from .serializers import (
    CommitUploadSerializer,
    ImportBatchListSerializer,
    ImportBatchSerializer,
    ValidateUploadSerializer,
)


class ImportBatchViewSet(
    TenantScopedViewSetMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Bulk data-import history + the validate / commit / template actions."""

    queryset = ImportBatch.objects.prefetch_related("errors").order_by(
        "-created_at"
    )
    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = {"default": "imports.run"}
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ["entity_type", "status"]
    ordering_fields = ["created_at", "committed_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ImportBatchListSerializer
        return ImportBatchSerializer

    def perform_destroy(self, instance):
        instance.delete(hard=True)

    @action(detail=False, methods=["get"], url_path="entity-types")
    def entity_types(self, request):
        """The catalogue of supported import entities + their columns."""
        from .entities import REGISTRY

        return Response({
            "entities": [
                {
                    "key": key,
                    "label": ImportEntityType(key).label,
                    "columns": definition.columns,
                    "required": sorted(definition.required),
                    "help": definition.template_help,
                }
                for key, definition in REGISTRY.items()
            ]
        })

    @action(detail=False, methods=["get"])
    def template(self, request):
        """Download a header-only CSV template for an entity type."""
        entity_type = request.query_params.get("entity_type")
        if entity_type not in {e.value for e in ImportEntityType}:
            return Response(
                {"error": {"detail": "Unknown entity_type."}}, status=400
            )
        body = services.template_csv(entity_type)
        response = HttpResponse(body, content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{entity_type}_import_template.csv"'
        )
        return response

    @action(detail=False, methods=["post"])
    def validate(self, request):
        """Parse + validate an upload. Returns a draft batch with errors."""
        payload = ValidateUploadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        uploaded = payload.validated_data["file"]
        batch = services.validate_batch(
            tenant=getattr(request, "tenant", None),
            entity_type=payload.validated_data["entity_type"],
            filename=uploaded.name,
            file_obj=uploaded,
            user=request.user,
        )
        record_audit(
            AuditAction.IMPORT, "imports.batch", entity_id=batch.pk,
            description=f"Validated {batch.entity_type} import "
                        f"({batch.valid_rows}/{batch.total_rows} clean)",
        )
        return Response(
            ImportBatchSerializer(batch, context={"request": request}).data,
            status=201,
        )

    @action(detail=True, methods=["post"])
    def commit(self, request, pk=None):
        """Re-validate the upload and create rows for every clean entry."""
        batch = self.get_object()
        payload = CommitUploadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        uploaded = payload.validated_data["file"]
        batch = services.commit_batch(
            batch=batch, file_obj=uploaded, filename=uploaded.name,
            user=request.user,
        )
        record_audit(
            AuditAction.IMPORT, "imports.batch", entity_id=batch.pk,
            description=f"Committed {batch.entity_type} import "
                        f"({batch.committed_rows} row(s) created)",
        )
        return Response(
            ImportBatchSerializer(batch, context={"request": request}).data
        )
