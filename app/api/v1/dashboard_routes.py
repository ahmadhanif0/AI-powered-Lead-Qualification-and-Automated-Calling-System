from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.lead import Lead

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _lead_qs(current_user: User, filter_user_id: Optional[int] = None):
    """
    Return a scoped queryset:
    - Regular user  → only their own leads
    - Admin         → all leads that have a user_id (no orphans)
                      optionally filtered to a specific user
    """
    if current_user.role == "admin":
        if filter_user_id:
            return Lead.filter(user_id=filter_user_id)
        # Exclude orphaned leads (user_id IS NULL) — pre-migration data
        return Lead.filter(user_id__isnull=False)
    return Lead.filter(user_id=current_user.id)


@router.get("/stats")
async def dashboard_stats(
    user_id: Optional[int] = Query(None, description="Admin only: filter by user"),
    current_user: User = Depends(get_current_user),
):
    qs = _lead_qs(current_user, user_id if current_user.role == "admin" else None)

    total_leads  = await qs.count()
    active_calls = await qs.filter(call_status="calling").count()
    booked       = await qs.filter(status="Booked").count()
    rejected     = await qs.filter(status="Rejected").count()

    return {
        "total_leads":  total_leads,
        "active_calls": active_calls,
        "booked":       booked,
        "rejected":     rejected,
    }


@router.get("/summary")
async def get_dashboard_summary(
    user_id: Optional[int] = Query(None, description="Admin only: filter by user"),
    current_user: User = Depends(get_current_user),
):
    qs    = _lead_qs(current_user, user_id if current_user.role == "admin" else None)
    leads = await qs.order_by("-updated_at")

    return {
        "total_leads": len(leads),
        "leads": [
            {
                "id":          l.id,
                "name":        f"{l.first_name or ''} {l.last_name or ''}".strip(),
                "email":       l.email,
                "phone":       l.phone,
                "company":     l.company,
                "score":       l.score,
                "status":      l.status,
                "stage":       l.lead_stage,
                "call_status": l.call_status,
                "ai_decision": l.ai_decision,
                "retry_count": l.retry_count,
                "updated_at":  l.updated_at.isoformat() if l.updated_at else None,
            }
            for l in leads
        ],
    }


@router.get("/live-leads")
async def live_leads(
    user_id: Optional[int] = Query(None, description="Admin only: filter by user"),
    current_user: User = Depends(get_current_user),
):
    qs = _lead_qs(current_user, user_id if current_user.role == "admin" else None)
    return await qs.order_by("-updated_at")
