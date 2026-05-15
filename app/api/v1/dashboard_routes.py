from fastapi import APIRouter

from app.models.lead import Lead

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/stats")
async def dashboard_stats():

    total_leads  = await Lead.all().count()
    hot_leads    = await Lead.filter(status="hot_lead").count()
    cold_leads   = await Lead.filter(status="cold_lead").count()
    active_calls = await Lead.filter(call_status="calling").count()

    return {
        "total_leads":  total_leads,
        "hot_leads":    hot_leads,
        "cold_leads":   cold_leads,
        "active_calls": active_calls,
    }


@router.get("/summary")
async def get_dashboard_summary():

    leads = await Lead.all().order_by("-updated_at")

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
                # Added: call_status and ai_decision for dashboard display
                "call_status": l.call_status,
                "ai_decision": l.ai_decision,
                "retry_count": l.retry_count,
                "updated_at":  l.updated_at.isoformat() if l.updated_at else None,
            }
            for l in leads
        ],
    }


@router.get("/live-leads")
async def live_leads():

    leads = await Lead.all().order_by("-updated_at")

    return leads
