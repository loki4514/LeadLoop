"""Celery application shared by the API (enqueue) and the worker (consume).

Redis is both broker and result backend. Tasks are defined in
``app.tasks`` and autodiscovered here; the FastAPI app enqueues them with
``.delay()`` / ``.apply_async()`` and the worker container runs
``celery -A app.core.celery_app.celery_app worker``.
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "leadagent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.ingestion", "app.tasks.followups"],
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,  # redeliver a task if the worker dies mid-run
    worker_prefetch_multiplier=1,  # fair dispatch for long ingestion jobs
    task_default_queue="default",
    result_expires=3600,
    # Periodic tasks (the worker runs with -B, embedding the beat scheduler).
    beat_schedule={
        "check-stalled-leads": {
            "task": "app.tasks.followups.check_stalled_leads",
            "schedule": settings.FOLLOWUP_CHECK_MINUTES * 60.0,
        },
    },
)
