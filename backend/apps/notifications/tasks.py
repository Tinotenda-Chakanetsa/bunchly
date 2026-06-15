"""Celery tasks for the notification engine.

Email delivery is done synchronously inside ``services.dispatch`` so
notifications work without a broker; these tasks exist for asynchronous
sending, the daily scheduled-alert job and failed-email retries.

Register the daily job as a ``django_celery_beat`` periodic task (the
project uses the database scheduler) pointing at ``run_scheduled_alerts``.
"""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("bunchly.notifications")


@shared_task(name="notifications.send_email", ignore_result=True)
def send_email_task(email_log_id: str) -> None:
    """Deliver a single queued ``EmailLog`` asynchronously."""
    from .models import EmailLog
    from .services import send_email

    email_log = EmailLog.objects.filter(pk=email_log_id).first()
    if email_log is None:
        logger.warning("send_email_task: EmailLog %s not found", email_log_id)
        return
    send_email(email_log)


@shared_task(name="notifications.retry_failed_emails", ignore_result=True)
def retry_failed_emails_task() -> int:
    """Re-attempt delivery of failed emails under the attempt ceiling."""
    from .services import retry_failed_emails

    retried = retry_failed_emails()
    logger.info("retry_failed_emails_task: retried %s email(s)", retried)
    return retried


@shared_task(name="notifications.run_scheduled_alerts", ignore_result=True)
def run_scheduled_alerts_task() -> dict:
    """Daily job — raise all date-triggered HR notifications."""
    from .scheduled import run_scheduled_alerts

    return run_scheduled_alerts()
