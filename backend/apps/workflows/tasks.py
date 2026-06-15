"""Celery tasks for the workflow engine."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("bunchly.workflows")


@shared_task(name="workflows.escalate_overdue", ignore_result=True)
def escalate_overdue_task() -> int:
    """Daily job — escalate workflow instances past their stage SLA."""
    from .services import escalate_overdue

    escalated = escalate_overdue()
    logger.info("escalate_overdue_task: escalated %s instance(s)", escalated)
    return escalated
