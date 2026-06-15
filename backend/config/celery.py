"""Celery application for Bunchly background jobs and scheduled tasks."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("bunchly")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:  # pragma: no cover
    """Smoke-test task: confirms the worker can execute jobs."""
    print(f"Celery request: {self.request!r}")
