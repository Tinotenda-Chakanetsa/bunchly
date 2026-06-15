"""Escalate workflow instances stuck past their stage SLA.

Wraps ``workflows.services.escalate_overdue`` so the escalation scan can
run manually or from cron, independent of Celery beat.
"""
from django.core.management.base import BaseCommand

from apps.workflows.services import escalate_overdue


class Command(BaseCommand):
    help = "Escalate workflow instances overdue against their stage SLA."

    def handle(self, *args, **options):
        escalated = escalate_overdue()
        self.stdout.write(
            self.style.SUCCESS(f"Escalated {escalated} overdue workflow instance(s).")
        )
