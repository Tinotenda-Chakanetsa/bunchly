"""Document business logic — upload validation, versioning, approval, expiry.

The viewsets stay thin: file rules (extension / size), version control and
the approval lifecycle all live here so they apply uniformly whether a
document is created or a new revision is added.
"""
from __future__ import annotations

import os
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .enums import DocumentStatus, VALID_STATUSES
from .models import Document, DocumentCategory, DocumentVersion


# --------------------------------------------------------------------------
# Upload limits & validation
# --------------------------------------------------------------------------
def resolve_upload_limits(category: DocumentCategory, tenant) -> tuple[list[str], int]:
    """Resolve (allowed extensions, max size in bytes) for a category.

    Precedence: category override -> tenant setting -> project default.
    Nothing organisation-specific is hard-coded.
    """
    tenant_settings = getattr(tenant, "settings", None)

    extensions = list(category.allowed_extensions or [])
    if not extensions and tenant_settings is not None:
        extensions = list(tenant_settings.allowed_upload_extensions or [])
    if not extensions:
        extensions = list(settings.ALLOWED_UPLOAD_EXTENSIONS)
    extensions = [e.lower().lstrip(".") for e in extensions]

    max_mb = category.max_file_size_mb
    if not max_mb and tenant_settings is not None:
        max_mb = tenant_settings.max_upload_size_mb or 0
    if not max_mb:
        max_mb = settings.MAX_UPLOAD_SIZE_MB
    return extensions, max_mb * 1024 * 1024


def validate_upload(uploaded_file, category: DocumentCategory, tenant) -> None:
    """Reject an upload whose type or size breaks the category's limits."""
    extensions, max_bytes = resolve_upload_limits(category, tenant)

    ext = os.path.splitext(uploaded_file.name)[1].lower().lstrip(".")
    if ext not in extensions:
        raise ValidationError(
            {"file": f"File type '.{ext}' is not permitted. "
                     f"Allowed: {', '.join('.' + e for e in extensions)}."}
        )
    if uploaded_file.size > max_bytes:
        raise ValidationError(
            {"file": f"File is too large ({uploaded_file.size // 1024} KB). "
                     f"Maximum is {max_bytes // (1024 * 1024)} MB."}
        )


# --------------------------------------------------------------------------
# Versioning & lifecycle
# --------------------------------------------------------------------------
def _initial_status(category: DocumentCategory) -> str:
    """A new/revised document is pending when its category needs approval."""
    return (
        DocumentStatus.PENDING
        if category.requires_approval
        else DocumentStatus.APPROVED
    )


def add_version(
    document: Document,
    uploaded_file,
    *,
    notes: str = "",
) -> DocumentVersion:
    """Attach a new file revision, making it the current version.

    Previous versions are retained (version control); only the
    ``is_current`` pointer moves. If the category requires approval the
    document returns to ``pending``.
    """
    validate_upload(uploaded_file, document.category, document.tenant)

    last = document.versions.order_by("-version_number").first()
    next_number = (last.version_number + 1) if last else 1

    document.versions.filter(is_current=True).update(is_current=False)
    version = DocumentVersion.objects.create(
        tenant=document.tenant,
        document=document,
        version_number=next_number,
        file=uploaded_file,
        original_filename=getattr(uploaded_file, "name", "")[:255],
        file_size=getattr(uploaded_file, "size", 0) or 0,
        content_type=getattr(uploaded_file, "content_type", "")[:120],
        is_current=True,
        notes=notes,
    )

    document.current_version = version
    if next_number > 1:
        # A revision re-opens approval and clears the stale review trail.
        document.status = _initial_status(document.category)
        document.reviewed_by = None
        document.reviewed_at = None
        document.review_note = ""
        document.save(
            update_fields=[
                "current_version", "status", "reviewed_by",
                "reviewed_at", "review_note", "updated_at",
            ]
        )
    else:
        document.save(update_fields=["current_version", "updated_at"])
    return version


def create_document(
    *,
    tenant,
    employee,
    category: DocumentCategory,
    title: str,
    uploaded_file,
    description: str = "",
    issue_date=None,
    expiry_date=None,
    is_confidential: bool = False,
) -> Document:
    """Create a document and its first version in one step."""
    document = Document.objects.create(
        tenant=tenant,
        employee=employee,
        category=category,
        title=title,
        description=description,
        issue_date=issue_date,
        expiry_date=expiry_date if category.tracks_expiry else None,
        is_confidential=is_confidential,
        status=_initial_status(category),
    )
    add_version(document, uploaded_file)
    return document


def approve_document(document: Document, *, user, note: str = "") -> Document:
    """HR approval — the document becomes valid for compliance counting."""
    if document.status not in {DocumentStatus.PENDING, DocumentStatus.REJECTED}:
        raise ValidationError("Only a pending or rejected document can be approved.")
    document.status = DocumentStatus.APPROVED
    document.reviewed_by = user
    document.reviewed_at = timezone.now()
    document.review_note = note[:255]
    document.save(
        update_fields=[
            "status", "reviewed_by", "reviewed_at", "review_note", "updated_at"
        ]
    )
    return document


def reject_document(document: Document, *, user, note: str = "") -> Document:
    """HR rejection — records the reason so the employee can re-upload."""
    if document.status not in {DocumentStatus.PENDING, DocumentStatus.APPROVED}:
        raise ValidationError("Only a pending or approved document can be rejected.")
    document.status = DocumentStatus.REJECTED
    document.reviewed_by = user
    document.reviewed_at = timezone.now()
    document.review_note = note[:255]
    document.save(
        update_fields=[
            "status", "reviewed_by", "reviewed_at", "review_note", "updated_at"
        ]
    )
    return document


# --------------------------------------------------------------------------
# Expiry & compliance
# --------------------------------------------------------------------------
def expire_documents(tenant=None, *, on_date=None) -> int:
    """Flip approved documents past their expiry date to ``expired``.

    Returns the number of documents transitioned. Safe to run repeatedly.
    """
    on_date = on_date or timezone.now().date()
    queryset = Document.objects.filter(
        status=DocumentStatus.APPROVED,
        expiry_date__isnull=False,
        expiry_date__lt=on_date,
    )
    if tenant is not None:
        queryset = queryset.filter(tenant=tenant)
    return queryset.update(status=DocumentStatus.EXPIRED, updated_at=timezone.now())


def expiring_documents(tenant, *, within_days: int = 30):
    """Approved documents whose expiry falls within ``within_days``."""
    today = timezone.now().date()
    horizon = today + timedelta(days=within_days)
    return Document.objects.filter(
        tenant=tenant,
        status=DocumentStatus.APPROVED,
        expiry_date__isnull=False,
        expiry_date__gte=today,
        expiry_date__lte=horizon,
    ).select_related("employee", "category")


def missing_required_categories(employee) -> list[DocumentCategory]:
    """Required categories the employee has no valid document for."""
    required = DocumentCategory.objects.filter(
        tenant=employee.tenant, is_required=True, is_active=True
    )
    held = set(
        Document.objects.filter(
            tenant=employee.tenant,
            employee=employee,
            status__in=VALID_STATUSES,
        ).values_list("category_id", flat=True)
    )
    return [c for c in required if c.id not in held]


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
# Internal document-event name -> notification-engine event key.
_EVENT_KEYS = {
    "approved": "document_approved",
    "rejected": "document_rejected",
}


def notify_document_event(document: Document, event: str, message: str = "") -> None:
    """Raise a document notification through the notification engine.

    ``message`` is retained for call-site readability; the engine renders
    the tenant's template instead.
    """
    event_key = _EVENT_KEYS.get(event)
    if event_key is None:
        return
    from apps.notifications import services as notifications

    notifications.dispatch(
        tenant=document.tenant,
        event_key=event_key,
        users=[getattr(document.employee, "user", None)],
        context={
            "document_title": document.title,
            "employee_name": document.employee.full_name,
            "note": document.review_note or "",
        },
        entity_type="documents.document",
        entity_id=str(document.pk),
    )
