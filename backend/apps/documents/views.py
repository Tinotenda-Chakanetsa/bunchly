"""Viewsets for the document-management module (spec §9.13).

Access scoping:
- ``documents.manage``  -> sees and manages every document in the tenant.
- ``documents.view``    -> sees non-sensitive documents + own documents.
- otherwise             -> sees only their own documents (self-service).

Sensitive-category and confidential documents are never exposed to a
plain viewer — only the owner and ``documents.manage`` holders. Uploads,
downloads, approvals and deletions are all written to the audit trail.
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.viewsets import TenantModelViewSet
from apps.employees.models import Employee

from . import services
from .models import Document, DocumentCategory
from .serializers import (
    DocumentCategorySerializer,
    DocumentCreateSerializer,
    DocumentListSerializer,
    DocumentMetaSerializer,
    DocumentReviewSerializer,
    DocumentSerializer,
    DocumentVersionSerializer,
    DocumentVersionUploadSerializer,
)


def _own_employee(request) -> Employee | None:
    """The employee record of the requesting user, if any."""
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


class DocumentCategoryViewSet(TenantModelViewSet):
    """Configurable document categories. Reading is open; managing is gated."""

    queryset = DocumentCategory.objects.all()
    serializer_class = DocumentCategorySerializer
    permission_required = {
        "create": "documents.manage",
        "update": "documents.manage",
        "partial_update": "documents.manage",
        "destroy": "documents.manage",
    }
    search_fields = ["name", "code"]
    filterset_fields = ["is_active", "is_required", "requires_approval", "is_sensitive"]
    ordering_fields = ["name", "created_at"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE, "documents.category",
            entity_id=serializer.instance.pk,
            description=f"Created document category {serializer.instance.name}",
        )

    def perform_update(self, serializer):
        serializer.save()
        record_audit(
            AuditAction.UPDATE, "documents.category",
            entity_id=serializer.instance.pk,
            description=f"Updated document category {serializer.instance.name}",
        )

    def perform_destroy(self, instance):
        pk, name = instance.pk, instance.name
        super().perform_destroy(instance)
        record_audit(
            AuditAction.DELETE, "documents.category",
            entity_id=pk, description=f"Archived document category {name}",
        )


class DocumentViewSet(TenantModelViewSet):
    """Employee documents — upload, versioning, approval, downloads."""

    queryset = Document.objects.select_related(
        "employee", "category", "current_version", "reviewed_by"
    ).prefetch_related("versions")
    permission_required = {
        "create": "documents.upload",
        "approve": "documents.approve",
        "reject": "documents.approve",
    }
    filterset_fields = ["employee", "category", "status", "is_confidential"]
    search_fields = ["title", "description", "employee__first_name", "employee__last_name"]
    ordering_fields = ["created_at", "expiry_date", "title"]

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentListSerializer
        if self.action in {"update", "partial_update"}:
            return DocumentMetaSerializer
        if self.action == "create":
            return DocumentCreateSerializer
        return DocumentSerializer

    # --- access scoping ---------------------------------------------------
    def _can_manage(self) -> bool:
        return self.request.user.has_perm_code(
            "documents.manage", getattr(self.request, "tenant", None)
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        tenant = getattr(self.request, "tenant", None)
        if self._can_manage():
            return queryset

        own = _own_employee(self.request)
        own_q = queryset.filter(employee=own) if own is not None else queryset.none()
        if user.has_perm_code("documents.view", tenant):
            # Org-wide viewers see everything except sensitive / confidential
            # documents that are not their own.
            shareable = queryset.filter(
                is_confidential=False, category__is_sensitive=False
            )
            return (shareable | own_q).distinct()
        return own_q

    # --- create / edit ----------------------------------------------------
    def create(self, request, *args, **kwargs):
        serializer = DocumentCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        tenant = self.get_tenant()
        employee = data["employee"]

        # A self-service uploader may only file documents for themselves.
        if not self._can_manage() and not request.user.has_perm_code(
            "documents.view", tenant
        ):
            own = _own_employee(request)
            if own is None or employee != own:
                raise PermissionDenied(
                    "You may only upload documents for yourself."
                )

        document = services.create_document(
            tenant=tenant,
            employee=employee,
            category=data["category"],
            title=data["title"],
            uploaded_file=data["file"],
            description=data.get("description", ""),
            issue_date=data.get("issue_date"),
            expiry_date=data.get("expiry_date"),
            is_confidential=data.get("is_confidential", False),
        )
        record_audit(
            AuditAction.UPLOAD, "documents.document", entity_id=document.pk,
            description=f"Uploaded document '{document.title}' for {employee}",
        )
        return Response(
            DocumentSerializer(document, context={"request": request}).data,
            status=201,
        )

    def _assert_can_edit(self, document) -> None:
        if self._can_manage():
            return
        own = _own_employee(self.request)
        if own is None or document.employee_id != own.id:
            raise PermissionDenied("You may only modify your own documents.")

    def perform_update(self, serializer):
        self._assert_can_edit(serializer.instance)
        serializer.save()
        record_audit(
            AuditAction.UPDATE, "documents.document",
            entity_id=serializer.instance.pk,
            description=f"Updated document '{serializer.instance.title}'",
        )

    def perform_destroy(self, instance):
        self._assert_can_edit(instance)
        pk, title = instance.pk, instance.title
        super().perform_destroy(instance)
        record_audit(
            AuditAction.DELETE, "documents.document", entity_id=pk,
            description=f"Deleted document '{title}'",
        )

    # --- versioning -------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="upload-version")
    def upload_version(self, request, pk=None):
        """Attach a new file revision to an existing document."""
        document = self.get_object()
        self._assert_can_edit(document)
        payload = DocumentVersionUploadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        version = services.add_version(
            document,
            payload.validated_data["file"],
            notes=payload.validated_data.get("notes", ""),
        )
        record_audit(
            AuditAction.UPLOAD, "documents.document", entity_id=document.pk,
            description=f"Uploaded v{version.version_number} of '{document.title}'",
        )
        return Response(
            DocumentSerializer(document, context={"request": request}).data
        )

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        """The full version history of a document."""
        document = self.get_object()
        serializer = DocumentVersionSerializer(
            document.versions.all(), many=True, context={"request": request}
        )
        return Response({"results": serializer.data})

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Return a link to a document version's file and log the access.

        ``?version=N`` selects a specific revision; the current version is
        used by default. With an S3 storage backend the URL is signed.
        """
        document = self.get_object()
        version_param = request.query_params.get("version")
        if version_param:
            version = document.versions.filter(
                version_number=version_param
            ).first()
        else:
            version = document.current_version
        if version is None or not version.file:
            raise NotFound("No file is available for this document.")

        record_audit(
            AuditAction.DOWNLOAD, "documents.document", entity_id=document.pk,
            description=f"Downloaded v{version.version_number} of '{document.title}'",
        )
        url = version.file.url
        return Response(
            {
                "document": str(document.pk),
                "version": version.version_number,
                "filename": version.original_filename,
                "content_type": version.content_type,
                "url": request.build_absolute_uri(url),
            }
        )

    # --- approval ---------------------------------------------------------
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """HR approval of a pending document."""
        document = self.get_object()
        payload = DocumentReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.approve_document(
            document, user=request.user, note=payload.validated_data.get("note", "")
        )
        record_audit(
            AuditAction.APPROVE, "documents.document", entity_id=document.pk,
            description=f"Approved document '{document.title}'",
        )
        services.notify_document_event(
            document, "approved", f"Your document '{document.title}' was approved."
        )
        return Response(
            DocumentSerializer(document, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """HR rejection of a document, with a reason."""
        document = self.get_object()
        payload = DocumentReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        note = payload.validated_data.get("note", "")
        services.reject_document(document, user=request.user, note=note)
        record_audit(
            AuditAction.REJECT, "documents.document", entity_id=document.pk,
            description=f"Rejected document '{document.title}'", reason=note,
        )
        services.notify_document_event(
            document, "rejected",
            f"Your document '{document.title}' was rejected. {note}".strip(),
        )
        return Response(
            DocumentSerializer(document, context={"request": request}).data
        )

    # --- self-service & compliance helpers -------------------------------
    @action(detail=False, url_path="my-documents")
    def my_documents(self, request):
        """The requesting user's own documents."""
        own = _own_employee(request)
        if own is None:
            raise NotFound("You do not have an employee profile in this organisation.")
        queryset = self.filter_queryset(
            self.get_queryset().filter(employee=own)
        )
        page = self.paginate_queryset(queryset)
        serializer = DocumentListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False)
    def expiring(self, request):
        """Approved documents expiring soon — ``?days=N`` (default 30)."""
        try:
            within = int(request.query_params.get("days", 30))
        except ValueError:
            within = 30
        documents = services.expiring_documents(
            getattr(request, "tenant", None), within_days=within
        )
        # Re-apply role scoping so a self-service user only sees their own.
        visible_ids = set(self.get_queryset().values_list("id", flat=True))
        documents = [d for d in documents if d.id in visible_ids]
        serializer = DocumentListSerializer(documents, many=True)
        return Response({"days": within, "results": serializer.data})

    @action(detail=False, url_path="missing-required")
    def missing_required(self, request):
        """Required categories an employee has no valid document for.

        ``?employee=<id>`` targets a specific employee (needs view/manage);
        otherwise the requesting user's own profile is used.
        """
        employee_id = request.query_params.get("employee")
        if employee_id:
            if not (
                self._can_manage()
                or request.user.has_perm_code(
                    "documents.view", getattr(request, "tenant", None)
                )
            ):
                raise PermissionDenied(
                    "You may only check your own required documents."
                )
            employee = Employee.objects.filter(
                tenant=getattr(request, "tenant", None), pk=employee_id
            ).first()
        else:
            employee = _own_employee(request)
        if employee is None:
            raise NotFound("Employee not found.")

        missing = services.missing_required_categories(employee)
        return Response(
            {
                "employee": str(employee.pk),
                "missing": DocumentCategorySerializer(
                    missing, many=True, context={"request": request}
                ).data,
            }
        )
