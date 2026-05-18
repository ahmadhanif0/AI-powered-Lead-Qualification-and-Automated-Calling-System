from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.call_log import CallLog

router = APIRouter(prefix="/users", tags=["Users"])


# ── Notification preferences ─────────────────────────────────────────

class NotificationSettingsRequest(BaseModel):
    email_on_interested:     Optional[bool] = None
    email_on_call_completed: Optional[bool] = None
    email_on_retry_failed:   Optional[bool] = None


@router.get("/notification-settings")
async def get_notification_settings(current_user: User = Depends(get_current_user)):
    return {
        "email_on_interested":     current_user.email_on_interested,
        "email_on_call_completed": current_user.email_on_call_completed,
        "email_on_retry_failed":   current_user.email_on_retry_failed,
    }


@router.put("/notification-settings")
async def update_notification_settings(
    body: NotificationSettingsRequest,
    current_user: User = Depends(get_current_user),
):
    if body.email_on_interested     is not None: current_user.email_on_interested     = body.email_on_interested
    if body.email_on_call_completed is not None: current_user.email_on_call_completed = body.email_on_call_completed
    if body.email_on_retry_failed   is not None: current_user.email_on_retry_failed   = body.email_on_retry_failed
    await current_user.save()

    return {
        "email_on_interested":     current_user.email_on_interested,
        "email_on_call_completed": current_user.email_on_call_completed,
        "email_on_retry_failed":   current_user.email_on_retry_failed,
    }


# ── Call recording access ─────────────────────────────────────────────

@router.get("/calls/{call_id}/recording")
async def get_call_recording(
    call_id: int,
    current_user: User = Depends(get_current_user),
):
    log = await CallLog.get_or_none(id=call_id)
    if not log:
        raise HTTPException(status_code=404, detail="Call log not found")

    # Ownership check
    if current_user.role != "admin" and log.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "call_id":        log.id,
        "recording_url":  log.recording_url,
        "transcript":     log.transcript,
        "ai_decision":    log.ai_decision,
        "duration_seconds": log.duration_seconds,
        "call_status":    log.call_status,
    }
