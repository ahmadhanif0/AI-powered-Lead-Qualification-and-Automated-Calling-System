from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.lead import Lead
from app.models.assistant import Assistant
from app.models.scheduled_call import ScheduledCall
from app.ai.call_service import CallService
from app.services.activity_logger import log_activity

router  = APIRouter(prefix="/calls", tags=["Calls"])
service = CallService()


# ── POST /calls/start/{lead_id} ──────────────────────────────────────

@router.post("/start/{lead_id}")
async def start_call(
    lead_id: int,
    current_user: User = Depends(get_current_user),
):
    lead = await Lead.get_or_none(id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if current_user.role != "admin" and lead.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await service.start_call(lead_id)
    await log_activity(current_user.id, "start_call", {"lead_id": lead_id})
    return {"message": "Call started successfully", "result": result}


# ── POST /calls/schedule ─────────────────────────────────────────────

class ScheduleCallRequest(BaseModel):
    lead_id:      int
    assistant_id: int
    scheduled_at: datetime   # ISO 8601 with timezone


@router.post("/schedule", status_code=201)
async def schedule_call(
    body: ScheduleCallRequest,
    current_user: User = Depends(get_current_user),
):
    # Validate scheduled_at is in the future
    now = datetime.now(timezone.utc)
    scheduled_at = body.scheduled_at
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    if scheduled_at <= now:
        raise HTTPException(status_code=400, detail="scheduled_at must be in the future")

    # Ownership checks
    lead = await Lead.get_or_none(id=body.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if current_user.role != "admin" and lead.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this lead")

    assistant = await Assistant.get_or_none(id=body.assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    if current_user.role != "admin" and assistant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this assistant")

    # Create record
    sc = await ScheduledCall.create(
        user_id=current_user.id,
        lead_id=body.lead_id,
        assistant_id=body.assistant_id,
        scheduled_at=scheduled_at,
        status="pending",
    )

    # Dispatch Celery task with countdown
    from app.queues.tasks import scheduled_call_task
    countdown = int((scheduled_at - now).total_seconds())
    task = scheduled_call_task.apply_async(args=[sc.id], countdown=countdown)

    sc.celery_task_id = task.id
    await sc.save()

    await log_activity(current_user.id, "schedule_call", {"scheduled_call_id": sc.id, "lead_id": body.lead_id})

    return {
        "id":           sc.id,
        "lead_id":      sc.lead_id,
        "assistant_id": sc.assistant_id,
        "scheduled_at": sc.scheduled_at.isoformat(),
        "status":       sc.status,
        "countdown_seconds": countdown,
    }


# ── GET /calls/scheduled ─────────────────────────────────────────────

@router.get("/scheduled")
async def list_scheduled_calls(current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        calls = await ScheduledCall.filter(status="pending").prefetch_related("lead", "assistant").order_by("scheduled_at")
    else:
        calls = await ScheduledCall.filter(user_id=current_user.id, status="pending").prefetch_related("lead", "assistant").order_by("scheduled_at")

    now = datetime.now(timezone.utc)
    return [
        {
            "id":           sc.id,
            "lead_id":      sc.lead_id,
            "lead_name":    f"{sc.lead.first_name or ''} {sc.lead.last_name or ''}".strip(),
            "assistant_id": sc.assistant_id,
            "assistant_name": sc.assistant.name,
            "scheduled_at": sc.scheduled_at.isoformat(),
            "status":       sc.status,
            "seconds_until": max(0, int((sc.scheduled_at - now).total_seconds())),
        }
        for sc in calls
    ]


# ── DELETE /calls/scheduled/{id} ─────────────────────────────────────

@router.delete("/scheduled/{sc_id}")
async def cancel_scheduled_call(
    sc_id: int,
    current_user: User = Depends(get_current_user),
):
    sc = await ScheduledCall.get_or_none(id=sc_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Scheduled call not found")
    if current_user.role != "admin" and sc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if sc.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot cancel a call with status '{sc.status}'")

    # Revoke Celery task
    if sc.celery_task_id:
        try:
            from app.queues.celery_app import celery_app
            celery_app.control.revoke(sc.celery_task_id, terminate=True)
        except Exception as e:
            pass  # Task may have already run

    sc.status = "cancelled"
    await sc.save()

    await log_activity(current_user.id, "cancel_scheduled_call", {"scheduled_call_id": sc_id})
    return {"message": "Scheduled call cancelled"}
