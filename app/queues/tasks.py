import asyncio
from datetime import datetime, timezone

from app.queues.celery_app import celery_app
from app.services.lead_sync_service import LeadSyncService
from app.ai.call_service import CallService
from app.logs.logger import logger
from app.database.db import init_db


def run_async(coro):
    """
    Run an async coroutine from a synchronous Celery task.

    Windows / solo-pool safe:
    - Reuses the existing event loop if it is still open.
    - Creates a new one only if the current loop is closed or missing.
    - Does NOT close the loop after use — closing it causes
      "RuntimeError: Event loop is closed" on Windows when Tortoise ORM
      or other libraries try to run cleanup callbacks after the coroutine
      returns.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


# =========================================================
# HUBSPOT SYNC TASK
# =========================================================

@celery_app.task(
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=60,
)
def sync_hubspot_leads_task(user_id: int = None):

    async def runner():
        await init_db()
        service = LeadSyncService()
        return await service.sync_hubspot_leads(user_id=user_id)

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
    """
    Direct retry task — called by poll_retry_queue_task inline.
    Also kept for any legacy apply_async calls still in flight.
    """
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
            # Reset to pending so the poller can pick it up again
            await retry_repo.reset_to_pending_for_lead(lead_id)
            raise

    return run_async(runner())


@celery_app.task
def scheduled_call_task(scheduled_call_id: int):
    """Fires a call for a ScheduledCall record at the scheduled time."""
    logger.info(f"SCHEDULED CALL TASK: scheduled_call_id={scheduled_call_id}")

    async def runner():
        await init_db()
        from app.models.scheduled_call import ScheduledCall

        sc = await ScheduledCall.get_or_none(id=scheduled_call_id)
        if not sc or sc.status not in ("pending", "processing"):
            logger.info(f"Scheduled call {scheduled_call_id} skipped (status={getattr(sc, 'status', 'not found')})")
            return

        service = CallService()
        try:
            result = await service.start_call(sc.lead_id, is_retry=False)
            sc.status = "completed"
            await sc.save()
            return result
        except Exception as e:
            logger.error(f"Scheduled call {scheduled_call_id} failed: {e}")
            # Reset to pending so poll_scheduled_calls_task retries it
            sc.status = "pending"
            await sc.save()
            raise

    return run_async(runner())


@celery_app.task
def poll_retry_queue_task():
    logger.info("POLL RETRY QUEUE: checking for overdue retries")

    async def runner():

        await init_db()

        from app.models.retry_queue import RetryQueue

        now = datetime.now(timezone.utc)

        # Pick up BOTH "pending" entries whose time has come AND any
        # "processing" entries that are overdue — these are stuck entries
        # from a previous poll cycle where the worker crashed or the
        # dispatched task never ran (common on Windows solo pool).
        overdue = await RetryQueue.filter(
            retry_status__in=["pending", "processing"],
            retry_at__lte=now,
        ).prefetch_related("lead").order_by("retry_at").all()

        logger.info(f"POLL RETRY QUEUE: found {len(overdue)} overdue retries")

        # ── Deduplicate by lead_id ───────────────────────────────────
        # If the VAPI webhook fired twice for the same call (status-update
        # + end-of-call-report both triggering handle_no_response), there
        # may be two entries for the same lead.  Process only the oldest
        # entry per lead; mark the rest as completed immediately.
        seen_lead_ids: set = set()
        deduplicated = []
        duplicates   = []

        for entry in overdue:
            if entry.lead_id in seen_lead_ids:
                duplicates.append(entry)
            else:
                seen_lead_ids.add(entry.lead_id)
                deduplicated.append(entry)

        # Clean up duplicates silently
        for dup in duplicates:
            dup.retry_status = "completed"
            await dup.save()
            logger.info(
                f"POLL RETRY QUEUE: cleaned duplicate entry {dup.id} "
                f"for lead {dup.lead_id}"
            )

        dispatched = 0

        for entry in deduplicated:
            try:
                lead = entry.lead

                if not lead:
                    logger.warning(f"Retry {entry.id} has no lead — marking failed")
                    entry.retry_status = "failed"
                    await entry.save()
                    continue

                # ── Active-call guard ────────────────────────────────
                # If a call is already in progress for this lead (e.g. a
                # previous retry is still dialling), skip this cycle so we
                # don't place two simultaneous calls.  The entry stays
                # "pending" and will be picked up on the next poll.
                fresh_lead = await lead.__class__.get_or_none(id=lead.id)
                if fresh_lead and fresh_lead.call_status in ("calling", "in-progress", "in_progress"):
                    logger.info(
                        f"POLL RETRY QUEUE: lead {lead.id} call_status="
                        f"'{fresh_lead.call_status}' — skipping retry {entry.id} "
                        f"(call already active)"
                    )
                    continue

                # Lock the entry to prevent duplicate dispatch on the
                # next poll cycle (60 s later).
                entry.retry_status = "processing"
                await entry.save()

                # ── Execute the call DIRECTLY — no .delay() / apply_async ──
                # On Windows solo pool, dispatching a new task from inside
                # a running task via .delay() is unreliable — the inner task
                # sits in Redis and may never be picked up while the poller
                # is still running.  Calling inline is safe because each
                # entry gets its own init_db() + CallService instance.
                service = CallService()
                await service.start_call(lead.id, is_retry=True)

                # Mark completed only after the call was successfully placed
                entry.retry_status = "completed"
                await entry.save()

                dispatched += 1
                logger.info(
                    f"POLL RETRY QUEUE: call placed for lead {lead.id} "
                    f"(retry {entry.id}, reason: {entry.retry_reason})"
                )

            except Exception as e:
                logger.error(
                    f"POLL RETRY QUEUE: failed for retry {entry.id} lead {getattr(entry, 'lead_id', '?')}: {e}"
                )
                # Reset to pending so the next poll cycle retries it.
                # Do NOT leave it as "processing" — that causes permanent sticking.
                try:
                    entry.retry_status = "pending"
                    await entry.save()
                except Exception as save_err:
                    logger.error(f"POLL RETRY QUEUE: could not reset retry {entry.id} to pending: {save_err}")

        return {
            "checked":    len(overdue),
            "duplicates": len(duplicates),
            "dispatched": dispatched,
        }

    return run_async(runner())


@celery_app.task
def poll_scheduled_calls_task():
    """
    Recovery poller — runs every 60 s via Celery Beat.
    Finds any ScheduledCall records whose scheduled_at has passed but
    whose status is still 'pending' (i.e. the original apply_async
    countdown task was lost because the worker was down).
    """
    logger.info("POLL SCHEDULED CALLS: checking for overdue scheduled calls")

    async def runner():
        await init_db()
        from app.models.scheduled_call import ScheduledCall

        now = datetime.now(timezone.utc)

        # Find all pending scheduled calls whose time has passed
        overdue = await ScheduledCall.filter(
            status="pending",
            scheduled_at__lte=now,
        ).all()

        logger.info(f"POLL SCHEDULED CALLS: found {len(overdue)} overdue")

        dispatched = 0
        for sc in overdue:
            try:
                # Mark as processing to prevent duplicate dispatch
                sc.status = "processing"
                await sc.save()

                service = CallService()
                result = await service.start_call(sc.lead_id, is_retry=False)
                sc.status = "completed"
                await sc.save()
                dispatched += 1
                logger.info(f"POLL SCHEDULED CALLS: fired call for scheduled_call_id={sc.id} lead_id={sc.lead_id}")
            except Exception as e:
                logger.error(f"POLL SCHEDULED CALLS: failed for scheduled_call_id={sc.id}: {e}")
                sc.status = "failed"
                await sc.save()

        return {"checked": len(overdue), "dispatched": dispatched}

    return run_async(runner())
