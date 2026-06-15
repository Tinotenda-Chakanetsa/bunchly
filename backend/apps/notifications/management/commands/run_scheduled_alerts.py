"""Run the date-triggered HR notification scan.

Wraps ``notifications.scheduled.run_scheduled_alerts`` so the daily job
can be triggered manually or from cron, independent of Celery beat.
"""
from django.core.management.base import BaseCommand

from apps.notifications.scheduled import run_scheduled_alerts


class Command(BaseCommand):
    help = "Scan all tenants and send date-triggered HR notifications."

    def handle(self, *args, **options):
        totals = run_scheduled_alerts()
        for category, count in totals.items():
            self.stdout.write(f"  {category}: {count}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Scheduled alerts complete — {sum(totals.values())} sent."
            )
        )
