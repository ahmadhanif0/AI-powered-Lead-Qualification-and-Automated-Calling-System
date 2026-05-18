from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_admin
from app.models.user import User
from app.models.lead import Lead
from app.models.assistant import Assistant
from app.models.call_log import CallLog
from app.models.retry_queue import RetryQueue

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


# ── GET /admin/analytics/overview ────────────────────────────────────

@router.get("/overview")
async def overview(_admin: User = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start  = today_start - timedelta(days=7)
    day_ago     = now - timedelta(hours=24)

    total_users     = await User.all().count()
    active_users    = await User.filter(is_active=True, is_suspended=False).count()
    suspended_users = await User.filter(is_suspended=True).count()

    total_calls     = await CallLog.all().count()
    calls_today     = await CallLog.filter(created_at__gte=today_start).count()
    calls_this_week = await CallLog.filter(created_at__gte=week_start).count()

    total_assistants = await Assistant.all().count()
    total_leads      = await Lead.all().count()

    active_users_24h = await User.filter(last_login__gte=day_ago).count()

    pending_retries = await RetryQueue.filter(retry_status="pending").count()
    failed_retries  = await RetryQueue.filter(retry_status="failed").count()

    return {
        "users": {
            "total":     total_users,
            "active":    active_users,
            "suspended": suspended_users,
            "active_last_24h": active_users_24h,
        },
        "calls": {
            "all_time":  total_calls,
            "today":     calls_today,
            "this_week": calls_this_week,
        },
        "assistants": total_assistants,
        "leads":       total_leads,
        "retry_queue": {
            "pending": pending_retries,
            "failed":  failed_retries,
        },
    }


# ── GET /admin/analytics/users/{user_id} ─────────────────────────────

@router.get("/users/{user_id}")
async def user_stats(user_id: int, _admin: User = Depends(require_admin)):
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    total_calls = await CallLog.filter(user_id=user_id).count()
    total_leads = await Lead.filter(user_id=user_id).count()

    # Duration average (only completed calls with duration)
    completed = await CallLog.filter(user_id=user_id, call_status="completed").all()
    durations = [c.duration_seconds for c in completed if c.duration_seconds]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    # Decision breakdown
    interested    = await Lead.filter(user_id=user_id, ai_decision="Interested").count()
    no_response   = await Lead.filter(user_id=user_id, ai_decision="No Response").count()
    retry_count   = await RetryQueue.filter(lead__user_id=user_id, retry_status="pending").count()

    interested_pct  = round(interested  / total_leads * 100, 1) if total_leads else 0
    no_response_pct = round(no_response / total_leads * 100, 1) if total_leads else 0

    return {
        "user_id":               user_id,
        "total_calls":           total_calls,
        "total_leads":           total_leads,
        "avg_call_duration_sec": avg_duration,
        "interested_percentage": interested_pct,
        "no_response_percentage": no_response_pct,
        "retry_queue_count":     retry_count,
    }


# ── GET /admin/analytics/assistants ──────────────────────────────────

@router.get("/assistants")
async def assistant_analytics(_admin: User = Depends(require_admin)):
    assistants = await Assistant.all()
    result = []
    for a in assistants:
        total = await CallLog.filter(assistant_name=a.name).count()
        completed = await CallLog.filter(assistant_name=a.name, call_status="completed").count()
        durations = [
            c.duration_seconds
            for c in await CallLog.filter(assistant_name=a.name, call_status="completed").all()
            if c.duration_seconds
        ]
        avg_dur = round(sum(durations) / len(durations), 1) if durations else 0
        success_rate = round(completed / total * 100, 1) if total else 0

        result.append({
            "assistant_id":    a.id,
            "name":            a.name,
            "owner_user_id":   a.user_id,
            "total_calls":     total,
            "success_rate":    success_rate,
            "avg_duration_sec": avg_dur,
        })

    return {"assistants": result}


# ── GET /admin/analytics/global ───────────────────────────────────────

@router.get("/global")
async def global_analytics(_admin: User = Depends(require_admin)):
    now = datetime.now(timezone.utc)

    # Calls per day for last 7 days
    calls_per_day = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = day_start + timedelta(days=1)
        count = await CallLog.filter(created_at__gte=day_start, created_at__lt=day_end).count()
        calls_per_day.append({
            "date":  day_start.strftime("%Y-%m-%d"),
            "calls": count,
        })

    # Decision ratio
    total_leads    = await Lead.all().count()
    interested     = await Lead.filter(ai_decision="Interested").count()
    rejected       = await Lead.filter(status="Rejected").count()
    wont_follow_up = await Lead.filter(status="Won't Follow Up").count()
    pending        = await Lead.filter(status="Pending").count()
    booked         = await Lead.filter(status="Booked").count()

    # Retry trends
    pending_retries = await RetryQueue.filter(retry_status="pending").count()
    failed_retries  = await RetryQueue.filter(retry_status="failed").count()
    done_retries    = await RetryQueue.filter(retry_status="completed").count()

    return {
        "calls_per_day": calls_per_day,
        "lead_status_breakdown": {
            "total":          total_leads,
            "Booked":         booked,
            "Rejected":       rejected,
            "Won't Follow Up": wont_follow_up,
            "Pending":        pending,
        },
        "retry_trends": {
            "pending":   pending_retries,
            "failed":    failed_retries,
            "completed": done_retries,
        },
    }
