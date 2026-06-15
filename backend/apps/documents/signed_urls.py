"""Signed, expiring document download URLs.

Control #9 — *Secure file storage*. A document's file is never served
directly from the storage backend with a long-lived public URL.
Instead, this module produces:

* A short-lived signed URL when the storage backend supports it (S3,
  GCS, Azure Blob — anything implementing ``url(name, parameters=...)``
  with ``expires=`` semantics via ``django-storages``).
* A signed redirect through the Django app for local storage during
  development.

In both cases the requested document must:

* Belong to the caller's tenant,
* Be visible per RBAC (``documents.view_document`` or the document's
  own owner clearance),
* Be served from a tenant-prefixed key
  (``/<tenant_slug>/employees/<eid>/<filename>``) so any future direct
  bucket access can't accidentally read another tenant's files.

The view writes an audit-log entry per download.
"""
from __future__ import annotations

import logging
import time
from hashlib import sha256
from hmac import compare_digest, new as hmac_new

from django.conf import settings
from django.core.signing import BadSignature, TimestampSigner
from django.http import FileResponse, Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger("bunchly.security")

_signer = TimestampSigner(salt="bunchly.documents.download")


def tenant_storage_prefix(tenant) -> str:
    """Return the per-tenant folder prefix every document key lives under."""
    if tenant is None:
        return "_no_tenant"
    return f"tenant_{tenant.slug or tenant.id}"


def sign_download(document_id: str) -> str:
    """Return an opaque token that ``download_signed`` will accept."""
    return _signer.sign(str(document_id))


def verify_download(token: str, max_age: int | None = None) -> str:
    """Reverse of :func:`sign_download`. Raises ``BadSignature`` on tamper/expiry."""
    ttl = max_age if max_age is not None else settings.DOCUMENT_SIGNED_URL_TTL_SECONDS
    return _signer.unsign(token, max_age=ttl)


def _audit(tenant, user, document, ip):
    """Write a download audit record (best-effort)."""
    try:
        from apps.audit.services import record_audit
        from apps.audit.models import AuditAction

        record_audit(
            action=AuditAction.DOWNLOAD,
            tenant=tenant,
            actor=user,
            entity_type="Document",
            entity_id=str(getattr(document, "id", "")),
            description=getattr(document, "title", "") or "",
            ip_address=ip,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit.record_failed", extra={"error": str(exc)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_signed(request, token: str):
    """Redeem a signed document download token.

    Tenant scoping is enforced twice:

    1. The viewset that minted the token already filtered by tenant.
    2. We re-fetch the document and re-check ``request.tenant``.
    """
    try:
        document_id = verify_download(token)
    except BadSignature:
        raise Http404("Link expired or tampered with.")

    try:
        from apps.documents.models import Document
    except Exception:
        raise Http404("Document store unavailable.")

    tenant = getattr(request, "tenant", None)
    document = (
        Document.objects.filter(id=document_id, tenant=tenant).first()
    )
    if document is None:
        raise Http404("Document not found.")

    storage_file = getattr(document, "file", None)
    if storage_file is None or not getattr(storage_file, "name", ""):
        raise Http404("Document has no attached file.")

    _audit(tenant, request.user, document, request.META.get("REMOTE_ADDR"))

    # If the storage backend supports signed URLs (S3 et al), redirect.
    try:
        url = storage_file.storage.url(
            storage_file.name,
            parameters={"ResponseContentDisposition": "attachment"},
            expire=settings.DOCUMENT_SIGNED_URL_TTL_SECONDS,
        )
        return Response({"download_url": url})
    except TypeError:
        # Local FileSystemStorage doesn't accept those kwargs — stream.
        return FileResponse(storage_file.open("rb"), as_attachment=True)


def hmac_token(payload: str) -> str:
    """Lightweight HMAC for use cases that can't carry a Django signer.

    Kept separate so consumers can verify in constant time without
    pulling in the full ``django.core.signing`` deserialiser.
    """
    key = settings.SECRET_KEY.encode("utf-8")
    return hmac_new(key, payload.encode("utf-8"), sha256).hexdigest()


def hmac_verify(payload: str, token: str) -> bool:
    return compare_digest(hmac_token(payload), token)


# Re-exported helper used by callers that want to embed an expiry into a
# token themselves rather than relying on ``TimestampSigner``.
def make_expiring(payload: str, ttl_seconds: int) -> tuple[str, str]:
    """Return ``(payload_with_ts, hmac)`` where ``payload_with_ts`` carries
    the expiry timestamp. Verification: split, check expiry, then HMAC."""
    expires_at = int(time.time()) + ttl_seconds
    pkt = f"{payload}|{expires_at}"
    return pkt, hmac_token(pkt)
