"""Viewsets and webhook endpoints for the notification engine.

- ``NotificationViewSet``         a user's own in-app notifications.
- ``NotificationTemplateViewSet`` admin template configuration.
- ``EmailLogViewSet``             read-only delivery audit + retry.
- ``InboundEmailViewSet``         read-only inbound-email metadata.
- webhook views                   provider delivery events + inbound mail.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.permissions import HasModulePermission, HasTenant
from apps.common.viewsets import TenantModelViewSet

from . import services
from .default_templates import DEFAULT_TEMPLATES
from .enums import EmailStatus, InboundEmailStatus
from .models import EmailLog, InboundEmail, Notification, NotificationTemplate
from .serializers import (
    EmailLogSerializer,
    InboundEmailSerializer,
    NotificationSerializer,
    NotificationTemplateSerializer,
    TestEmailSerializer,
)

logger = logging.getLogger("bunchly.notifications")


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """A user's own in-app notifications, with read-state actions."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, HasTenant]
    filterset_fields = ["event_key", "is_read", "level"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        return Notification.objects.filter(
            tenant=tenant, recipient=self.request.user
        )

    @action(detail=False, url_path="unread-count")
    def unread_count(self, request):
        """Number of unread notifications — for the top-bar badge."""
        return Response({"unread": self.get_queryset().filter(is_read=False).count()})

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        """Mark one notification as read."""
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at", "updated_at"])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        """Mark every unread notification as read."""
        updated = self.get_queryset().filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"marked_read": updated})


class NotificationTemplateViewSet(TenantModelViewSet):
    """Configurable notification templates — admin only."""

    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_required = {
        "create": "notifications.configure",
        "update": "notifications.configure",
        "partial_update": "notifications.configure",
        "destroy": "notifications.configure",
        "seed_defaults": "notifications.configure",
        "test_email": "notifications.configure",
    }
    search_fields = ["name", "event_key", "subject"]
    filterset_fields = ["channel", "is_enabled", "event_key"]
    ordering_fields = ["name", "created_at"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE, "notifications.template",
            entity_id=serializer.instance.pk,
            description=f"Created notification template {serializer.instance.name}",
        )

    def perform_update(self, serializer):
        serializer.save()
        record_audit(
            AuditAction.UPDATE, "notifications.template",
            entity_id=serializer.instance.pk,
            description=f"Updated notification template {serializer.instance.name}",
        )

    @action(detail=False, methods=["post"], url_path="seed-defaults")
    def seed_defaults(self, request):
        """Create any missing templates from the built-in catalogue."""
        tenant = self.get_tenant()
        created = 0
        for event_key, cfg in DEFAULT_TEMPLATES.items():
            _, was_created = NotificationTemplate.objects.get_or_create(
                tenant=tenant,
                event_key=event_key,
                defaults={
                    "name": cfg["name"],
                    "channel": cfg["channel"],
                    "subject": cfg["subject"],
                    "body": cfg["body"],
                },
            )
            created += int(was_created)
        return Response({"created": created, "total": len(DEFAULT_TEMPLATES)})

    @action(detail=False, methods=["post"], url_path="test-email")
    def test_email(self, request):
        """Send a test email to verify the tenant's email configuration."""
        payload = TestEmailSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        email_log = services.send_test_email(
            self.get_tenant(), payload.validated_data["to_email"]
        )
        record_audit(
            AuditAction.UPDATE, "notifications.email_log", entity_id=email_log.pk,
            description=f"Sent test email to {email_log.to_email}",
        )
        return Response(EmailLogSerializer(email_log).data)


class EmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only outbound-email delivery audit, with retry actions."""

    serializer_class = EmailLogSerializer
    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "notifications.configure"
    filterset_fields = ["status", "event_key"]
    search_fields = ["to_email", "subject"]
    ordering_fields = ["created_at", "sent_at"]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        return EmailLog.objects.filter(tenant=tenant)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Re-attempt delivery of a single failed email."""
        email_log = self.get_object()
        if email_log.status == EmailStatus.SENT:
            raise ValidationError("This email has already been sent.")
        services.send_email(email_log)
        return Response(self.get_serializer(email_log).data)

    @action(detail=False, methods=["post"], url_path="retry-failed")
    def retry_failed(self, request):
        """Re-attempt every failed email for the tenant."""
        retried = services.retry_failed_emails(getattr(request, "tenant", None))
        return Response({"retried": retried})


class InboundEmailViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view of received inbound emails."""

    serializer_class = InboundEmailSerializer
    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "notifications.configure"
    filterset_fields = ["status"]
    search_fields = ["from_email", "subject"]
    ordering_fields = ["created_at", "received_at"]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        return InboundEmail.objects.filter(tenant=tenant)


# --------------------------------------------------------------------------
# Webhook endpoints (provider callbacks — authenticated by a shared secret)
# --------------------------------------------------------------------------
def _webhook_authorised(request) -> bool:
    """Validate the shared webhook secret. Fails closed when unconfigured."""
    secret = getattr(settings, "NOTIFICATIONS_WEBHOOK_SECRET", "")
    if not secret:
        return False
    supplied = request.headers.get("X-Webhook-Secret") or request.query_params.get(
        "secret", ""
    )
    return supplied == secret


# Provider delivery-event -> EmailLog status.
_DELIVERY_EVENT_STATUS = {
    "email.delivered": EmailStatus.SENT,
    "email.sent": EmailStatus.SENT,
    "email.bounced": EmailStatus.FAILED,
    "email.complained": EmailStatus.FAILED,
    "email.delivery_delayed": EmailStatus.QUEUED,
}


@api_view(["POST"])
@permission_classes([AllowAny])
def email_delivery_webhook(request):
    """Receive provider delivery events and update the matching EmailLog."""
    if not _webhook_authorised(request):
        return Response({"detail": "Unauthorised."}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data if isinstance(request.data, dict) else {}
    event_type = payload.get("type", "")
    data = payload.get("data", {}) or {}
    message_id = data.get("email_id") or data.get("id") or ""

    new_status = _DELIVERY_EVENT_STATUS.get(event_type)
    if message_id and new_status:
        updated = EmailLog.objects.filter(
            provider_message_id=message_id
        ).update(status=new_status, updated_at=timezone.now())
        logger.info("delivery webhook %s -> %s row(s)", event_type, updated)
        return Response({"matched": updated})
    return Response({"matched": 0})


@api_view(["POST"])
@permission_classes([AllowAny])
def inbound_email_webhook(request):
    """Store an inbound email's metadata (inbound-routing readiness).

    Per spec, complex routing is not implemented — the email is stored and
    a best-effort tenant match is made from the recipient address domain.
    """
    if not _webhook_authorised(request):
        return Response({"detail": "Unauthorised."}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data if isinstance(request.data, dict) else {}
    from_email = payload.get("from", "") or payload.get("from_email", "")
    if not from_email:
        raise ValidationError({"from": "A sender address is required."})

    to_email = payload.get("to", "") or payload.get("to_email", "")
    tenant = _match_tenant_by_email(to_email)
    inbound = InboundEmail.objects.create(
        tenant=tenant,
        from_email=from_email,
        to_email=to_email,
        subject=payload.get("subject", "")[:255],
        body=payload.get("text", "") or payload.get("body", ""),
        provider=payload.get("provider", ""),
        provider_message_id=payload.get("message_id", "") or payload.get("id", ""),
        received_at=timezone.now(),
        raw_payload=payload,
        status=(
            InboundEmailStatus.RECEIVED if tenant else InboundEmailStatus.UNMATCHED
        ),
    )
    return Response({"id": str(inbound.pk), "status": inbound.status}, status=201)


def _match_tenant_by_email(address: str):
    """Best-effort tenant match from a recipient address (subdomain hint)."""
    if not address or "@" not in address:
        return None
    from apps.tenants.models import TenantDomain

    local, _, domain = address.partition("@")
    hint = (domain.split(".")[0] or local).lower()
    match = TenantDomain.objects.filter(domain__iexact=hint).select_related(
        "tenant"
    ).first()
    return match.tenant if match else None
