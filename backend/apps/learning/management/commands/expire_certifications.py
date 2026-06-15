"""Expire training certifications whose validity window has passed.

Idempotent — intended to run daily (e.g. a Celery beat task). Operates
across every tenant.
"""
from django.core.management.base import BaseCommand

from apps.learning.services import expire_certifications


class Command(BaseCommand):
    help = "Mark completed training records with lapsed certifications as expired."

    def handle(self, *args, **options):
        transitioned = expire_certifications()
        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {transitioned} lapsed training certification(s)."
            )
        )
