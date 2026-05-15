from fastapi import APIRouter

from app.repositories.retry_queue_repository import (
    RetryQueueRepository
)

router = APIRouter(
    prefix="/retries",
    tags=["Retries"]
)


@router.get("/")
async def get_retry_queue():

    retries = (
        await RetryQueueRepository
        .get_pending_retries()
    )
    print(retries)

    return [
        {
            "id": retry.id,
            "lead_id": retry.lead_id,
            "lead_name": (
                f"{retry.lead.first_name} "
                f"{retry.lead.last_name}"
            ),
            "reason": retry.retry_reason,
            "status": retry.retry_status,
            "retry_at": retry.retry_at
        }
        for retry in retries
    ]