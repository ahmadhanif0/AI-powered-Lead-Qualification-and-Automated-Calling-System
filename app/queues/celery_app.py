import sys

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings


celery_app = Celery(
    "ai_lead_system",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "poll-retry-queue-every-minute": {
            "task": "app.queues.tasks.poll_retry_queue_task",
            "schedule": 60.0,  # every 60 seconds
        },
        "poll-scheduled-calls-every-minute": {
            "task": "app.queues.tasks.poll_scheduled_calls_task",
            "schedule": 60.0,  # every 60 seconds — catches any missed scheduled calls
        },
        "sync-hubspot-every-hour": {
            "task": "app.queues.tasks.sync_hubspot_leads_task",
            "schedule": crontab(minute=0),  # top of every hour
        },
    },
)

# ── Windows compatibility fix ────────────────────────────────────────
# The default Celery pool (prefork) uses billiard/multiprocessing shared
# memory handles that are broken on Windows, causing:
#   OSError: [WinError 6] The handle is invalid
# Fix: use the 'solo' pool on Windows (single-threaded, no subprocess).
# On Linux/macOS (production), prefork is used as normal.
if sys.platform == "win32":
    celery_app.conf.worker_pool = "solo"
    celery_app.conf.worker_concurrency = 1

from app.queues import tasks