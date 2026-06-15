"""Notification dispatch — the single entry point every module calls.

``dispatch`` resolves the tenant's template for an event, renders it,
creates in-app ``Notification`` rows and queues ``EmailLog`` rows, then
delivers email through the configured provider (Resend or SMTP).

Design notes:
- Email configuration is never hard-coded — provider, keys and the
  per-tenant sender identity are read from settings / ``TenantSettings``.
- Dispatch is defensive: a missing template, a disabled notification or
  a delivery failure never raises into the caller's request.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings
from django.core.mail import EmailMessage
from django.template import Context, Template
from django.utils import timezone

from .default_templates import DEFAULT_TEMPLATES
from .enums import EmailStatus, NotificationChannel
from .models import EmailLog, Notification, NotificationTemplate

logger = logging.getLogger("bunchly.notifications")

MAX_EMAIL_ATTEMPTS = 3


@dataclass
class ResolvedTemplate:
    """A template ready to render — DB row or built-in fallback."""

    event_key: str
    channel: str
    subject: str
    body: str
    is_enabled: bool


# --------------------------------------------------------------------------
# Template resolution & rendering
# --------------------------------------------------------------------------
def get_template(tenant, event_key: str) -> ResolvedTemplate | None:
    """Resolve a tenant's template for an event, falling back to built-ins.

    Returns ``None`` if the event is unknown. A disabled DB row is
    returned with ``is_enabled=False`` so the caller can skip it.
    """
    row = (
        NotificationTemplate.objects.filter(tenant=tenant, event_key=event_key)
        .first()
        if tenant is not None
        else None
    )
    if row is not None:
        return ResolvedTemplate(
            event_key=event_key,
            channel=row.channel,
            subject=row.subject,
            body=row.body,
            is_enabled=row.is_enabled,
        )
    default = DEFAULT_TEMPLATES.get(event_key)
    if default is None:
        return None
    return ResolvedTemplate(
        event_key=event_key,
        channel=default["channel"],
        subject=default["subject"],
        body=default["body"],
        is_enabled=True,
    )


def render(text: str, context: dict) -> str:
    """Render a template string against a context (no HTML autoescaping)."""
    try:
        ctx = Context(context or {}, autoescape=False)
        return Template(text).render(ctx).strip()
    except Exception:  # pragma: no cover - a bad template must not break send
        logger.exception("Failed to render notification template")
        return text


# --------------------------------------------------------------------------
# Sender identity & delivery
# --------------------------------------------------------------------------
def _sender_identity(tenant) -> tuple[str, str]:
    """Resolve (from_email, reply_to) — per-tenant override then defaults."""
    from_email = settings.DEFAULT_FROM_EMAIL
    reply_to = settings.DEFAULT_REPLY_TO_EMAIL or ""
    tenant_settings = getattr(tenant, "settings", None)
    if tenant_settings is not None:
        if tenant_settings.email_sender_name:
            from_email = f"{tenant_settings.email_sender_name} <{from_email}>"
        if tenant_settings.email_reply_to:
            reply_to = tenant_settings.email_reply_to
    return from_email, reply_to


def _deliver(*, to_email: str, subject: str, body: str, from_email: str,
             reply_to: str) -> tuple[str, str]:
    """Send one email through the configured provider.

    Returns ``(provider, provider_message_id)``. Raises on failure so the
    caller can record it and retry.
    """
    provider = (settings.EMAIL_PROVIDER or "smtp").lower()
    if provider == "resend" and settings.RESEND_API_KEY:
        import resend  # provider SDK — declared in requirements

        resend.api_key = settings.RESEND_API_KEY
        params: dict = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "text": body,
        }
        if reply_to:
            params["reply_to"] = [reply_to]
        result = resend.Emails.send(params)
        return "resend", (result or {}).get("id", "")

    # SMTP / Django mail backend fallback.
    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[to_email],
        reply_to=[reply_to] if reply_to else None,
    )
    message.send(fail_silently=False)
    return "smtp", ""


def send_email(email_log: EmailLog) -> EmailLog:
    """Attempt delivery of one ``EmailLog`` and record the outcome."""
    email_log.attempts += 1
    try:
        provider, message_id = _deliver(
            to_email=email_log.to_email,
            subject=email_log.subject,
            body=email_log.body,
            from_email=email_log.from_email,
            reply_to=email_log.reply_to,
        )
        email_log.status = EmailStatus.SENT
        email_log.provider = provider
        email_log.provider_message_id = message_id
        email_log.sent_at = timezone.now()
        email_log.error_message = ""
        logger.info("email sent to %s (%s)", email_log.to_email, provider)
    except Exception as exc:  # delivery failed — keep for retry
        email_log.status = EmailStatus.FAILED
        email_log.error_message = str(exc)[:500]
        logger.warning("email to %s failed: %s", email_log.to_email, exc)
    email_log.save(
        update_fields=[
            "attempts", "status", "provider", "provider_message_id",
            "sent_at", "error_message", "updated_at",
        ]
    )
    return email_log


def queue_email(
    *,
    tenant,
    to_email: str,
    subject: str,
    body: str,
    event_key: str = "",
    notification: Notification | None = None,
    send_now: bool = True,
) -> EmailLog:
    """Create an ``EmailLog`` and (by default) attempt delivery immediately.

    ``send_now=False`` leaves the row queued for the Celery task / retry
    job to pick up.
    """
    from_email, reply_to = _sender_identity(tenant)
    email_log = EmailLog.objects.create(
        tenant=tenant,
        event_key=event_key,
        to_email=to_email,
        from_email=from_email,
        reply_to=reply_to,
        subject=subject,
        body=body,
        notification=notification,
    )
    if send_now:
        send_email(email_log)
    return email_log


# --------------------------------------------------------------------------
# Dispatch — the public entry point
# --------------------------------------------------------------------------
def dispatch(
    *,
    tenant,
    event_key: str,
    users=None,
    extra_emails=None,
    context: dict | None = None,
    level: str = "info",
    url: str = "",
    entity_type: str = "",
    entity_id: str = "",
    send_now: bool = True,
) -> list[Notification]:
    """Raise a notification event.

    ``users``        recipients that get an in-app notification + email.
    ``extra_emails`` addresses that get the email only (e.g. a tenant's
                     configured finance recipients).

    Returns the in-app ``Notification`` rows created (may be empty). Never
    raises — notification delivery must not break the originating action.
    """
    notifications: list[Notification] = []
    try:
        template = get_template(tenant, event_key)
        if template is None:
            logger.warning("dispatch: unknown event_key '%s'", event_key)
            return notifications
        if not template.is_enabled:
            logger.info("dispatch: '%s' disabled for tenant", event_key)
            return notifications

        context = context or {}
        subject = render(template.subject, context)
        body = render(template.body, context)
        users = [u for u in (users or []) if u is not None]
        wants_inapp = template.channel in {
            NotificationChannel.IN_APP, NotificationChannel.BOTH
        }
        wants_email = template.channel in {
            NotificationChannel.EMAIL, NotificationChannel.BOTH
        }

        by_user: dict = {}
        if wants_inapp:
            for user in users:
                note = Notification.objects.create(
                    tenant=tenant,
                    recipient=user,
                    event_key=event_key,
                    title=subject,
                    body=body,
                    level=level,
                    url=url,
                    entity_type=entity_type,
                    entity_id=str(entity_id),
                )
                notifications.append(note)
                by_user[user.pk] = note

        if wants_email:
            seen: set[str] = set()
            for user in users:
                addr = (getattr(user, "email", "") or "").lower()
                if addr and addr not in seen:
                    seen.add(addr)
                    queue_email(
                        tenant=tenant, to_email=user.email, subject=subject,
                        body=body, event_key=event_key,
                        notification=by_user.get(user.pk), send_now=send_now,
                    )
            for addr in extra_emails or []:
                norm = (addr or "").lower()
                if norm and norm not in seen:
                    seen.add(norm)
                    queue_email(
                        tenant=tenant, to_email=addr, subject=subject,
                        body=body, event_key=event_key, send_now=send_now,
                    )
    except Exception:  # pragma: no cover - dispatch must never raise
        logger.exception("notification dispatch failed for '%s'", event_key)
    return notifications


def notify_user(user, event_key: str, *, context=None, **kwargs) -> list[Notification]:
    """Dispatch to a single user, resolving their default tenant.

    Useful for pre-/cross-tenant flows (e.g. password reset) where the
    caller has a user but no request tenant.
    """
    tenant = None
    if hasattr(user, "memberships"):
        membership = (
            user.memberships.filter(is_default=True).first()
            or user.memberships.first()
        )
        if membership is not None:
            tenant = membership.tenant
    return dispatch(
        tenant=tenant, event_key=event_key, users=[user],
        context=context, **kwargs,
    )


# --------------------------------------------------------------------------
# Retry & test
# --------------------------------------------------------------------------
def retry_failed_emails(tenant=None, *, max_attempts: int = MAX_EMAIL_ATTEMPTS) -> int:
    """Re-attempt delivery of failed emails under the attempt ceiling."""
    queryset = EmailLog.objects.filter(
        status=EmailStatus.FAILED, attempts__lt=max_attempts
    )
    if tenant is not None:
        queryset = queryset.filter(tenant=tenant)
    retried = 0
    for email_log in queryset:
        send_email(email_log)
        retried += 1
    return retried


def send_test_email(tenant, to_email: str) -> EmailLog:
    """Send a test email to verify a tenant's email configuration."""
    return queue_email(
        tenant=tenant,
        to_email=to_email,
        subject="Bunchly test email",
        body=(
            "This is a test email from Bunchly. If you received it, your "
            "organisation's email configuration is working."
        ),
        event_key="",
    )
