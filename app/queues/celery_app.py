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
    # FIX (Issue 1): periodic beat schedule — polls retry_queue every
    # minute for overdue entries that were never picked up (e.g. worker
    # was down when apply_async fired).
    beat_schedule={
        "poll-retry-queue-every-minute": {
            "task": "app.queues.tasks.poll_retry_queue_task",
            "schedule": 60.0,  # every 60 seconds
        },
        "sync-hubspot-every-hour": {
            "task": "app.queues.tasks.sync_hubspot_leads_task",
            "schedule": crontab(minute=0),  # top of every hour
        },
    },
)

from app.queues import tasks