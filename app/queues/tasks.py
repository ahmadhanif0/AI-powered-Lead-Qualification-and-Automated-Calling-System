import asyncio
from datetime import datetime, timezone

from app.queues.celery_app import celery_app
from app.services.lead_sync_service import LeadSyncService
from app.ai.call_service import CallService
from app.logs.logger import logger
from app.database.db import init_db


def run_async(coro):

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coro)

    finally:
        loop.close()


# =========================================================
# HUBSPOT SYNC TASK
# =========================================================

@celery_app.task(
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=60,    # 1 minute between sync retries
)
def sync_hubspot_leads_task():

    async def runner():

        await init_db()

        service = LeadSyncService()

        return await service.sync_hubspot_leads()

    return run_async(runner())


# =========================================================
# AI CALL TASK
# =========================================================

@celery_app.task
def start_lead_call_task(lead_id: int):

    async def runner():

        await init_db()

        service = CallService()

        return await service.start_call(lead_id)

    return run_async(runner())


@celery_app.task(
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=300,   # 5 minutes between automatic retries
    retry_backoff=True,        # exponential: 5m, 10m, 20m
)
def retry_call_task(lead_id: int):

    logger.info(f"RETRY TASK STARTED FOR LEAD: {lead_id}")

    async def runner():

        await init_db()

        from app.repositories.retry_queue_repository import RetryQueueRepository

        retry_repo = RetryQueueRepository()
        service = CallService()

        try:
            result = await service.start_call(lead_id, is_retry=True)
            # Call placed successfully — close out the retry entry
            await retry_repo.mark_completed_for_lead(lead_id)
            return result

        except Exception as e:
            logger.error(f"RETRY TASK FAILED FOR LEAD {lead_id}: {e}")
            await retry_repo.mark_failed_for_lead(lead_id)
            raise

    return run_async(runner())


@celery_app.task
def poll_retry_queue_task():

    logger.info("POLL RETRY QUEUE: checking for overdue retries")

    async def runner():

        await init_db()

        from app.repositories.retry_queue_repository import RetryQueueRepository
        from app.models.retry_queue import RetryQueue

        repo = RetryQueueRepository()
        now = datetime.now(timezone.utc)

        # Fetch all pending retries whose retry_at has passed
        overdue = await RetryQueue.filter(
            retry_status="pending",
            retry_at__lte=now
        ).prefetch_related("lead").all()

        logger.info(f"POLL RETRY QUEUE: found {len(overdue)} overdue retries")

        dispatched = 0

        for entry in overdue:
            try:
                lead = entry.lead

                if not lead:
                    logger.warning(f"Retry {entry.id} has no lead — skipping")
                    # Mark as failed so it doesn't loop
                    entry.retry_status = "failed"
                    await entry.save()
                    continue

                # Mark as processing before dispatching to prevent
                # duplicate dispatch on the next poll cycle
                entry.retry_status = "processing"
                await entry.save()

                # Dispatch the call task
                retry_call_task.delay(lead.id)

                dispatched += 1

                logger.info(
                    f"POLL RETRY QUEUE: dispatched call for lead {lead.id} "
                    f"(retry {entry.id}, reason: {entry.retry_reason})"
                )

            except Exception as e:
                logger.error(
                    f"POLL RETRY QUEUE: error processing retry {entry.id}: {e}"
                )

        return {
            "checked": len(overdue),
            "dispatched": dispatched
        }

    return run_async(runner())