from app.models.retry_queue import RetryQueue
from app.logs.logger import logger


class RetryQueueRepository:

    @staticmethod
    async def create_retry(data: dict):

        lead_id = data.get("lead_id")

        if not lead_id:
            raise Exception(
                "lead_id missing — cannot create retry"
            )

        logger.info(
            f"Creating retry for lead_id: {lead_id}"
        )

        retry = await RetryQueue.create(
            lead_id=int(lead_id),
            retry_reason=data["retry_reason"],
            retry_status=data.get(
                "retry_status",
                "pending"
            ),
            retry_at=data["retry_at"]
        )

        logger.info(
            f"Retry created successfully: {retry.id}"
        )

        return retry

    @staticmethod
    async def get_pending_retries():

        retries = await (
            RetryQueue
            .filter(retry_status="pending")
            .prefetch_related("lead")
            .all()
        )

        logger.info(
            f"Pending retries fetched: {len(retries)}"
        )

        return retries

    @staticmethod
    async def mark_completed_for_lead(lead_id: int):
        """Mark all processing/pending retries for a lead as completed."""
        await RetryQueue.filter(
            lead_id=lead_id,
            retry_status__in=["pending", "processing"]
        ).update(retry_status="completed")

        logger.info(
            f"Marked retries as completed for lead_id: {lead_id}"
        )

    @staticmethod
    async def mark_failed_for_lead(lead_id: int):
        """Mark processing retries as failed (call could not be placed)."""
        await RetryQueue.filter(
            lead_id=lead_id,
            retry_status="processing"
        ).update(retry_status="failed")

        logger.info(
            f"Marked retries as failed for lead_id: {lead_id}"
        )