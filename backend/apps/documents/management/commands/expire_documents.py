"""Transition approved documents past their expiry date to ``expired``.

Idempotent — intended to run daily (e.g. a Celery beat task). Operates
across every tenant.
"""
from django.core.management.base import BaseCommand

from apps.documents.services import expire_documents


class Command(BaseCommand):
    help = "Mark approved documents whose expiry date has passed as expired."

    def handle(self, *args, **options):
        transitioned = expire_documents()
        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {transitioned} document(s) past their expiry date."
            )
        )
