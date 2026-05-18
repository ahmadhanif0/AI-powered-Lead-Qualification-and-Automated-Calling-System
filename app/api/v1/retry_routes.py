from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.retry_queue import RetryQueue

router = APIRouter(prefix="/retries", tags=["Retries"])


@router.get("/")
async def get_retry_queue(current_user: User = Depends(get_current_user)):
    # Filter retries whose lead belongs to the current user
    if current_user.role == "admin":
        retries = await RetryQueue.filter(
            retry_status__in=["pending", "processing"]
        ).prefetch_related("lead").all()
    else:
        retries = await RetryQueue.filter(
            retry_status__in=["pending", "processing"],
            lead__user_id=current_user.id,
        ).prefetch_related("lead").all()

    return [
        {
            "id":           r.id,
            "lead_id":      r.lead_id,
            "lead_name":    f"{r.lead.first_name or ''} {r.lead.last_name or ''}".strip(),
            "retry_reason": r.retry_reason,
            "retry_status": r.retry_status,
            "retry_at":     r.retry_at,
        }
        for r in retries
    ]
