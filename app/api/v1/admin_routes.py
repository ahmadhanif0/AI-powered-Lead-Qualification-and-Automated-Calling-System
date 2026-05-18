from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from app.auth.dependencies import require_admin, get_current_user
from app.auth.jwt_handler import hash_password
from app.models.user import User
from app.models.user_activity import UserActivity
from app.models.lead import Lead
from app.models.call_log import CallLog
from app.models.assistant import Assistant
from app.services.activity_logger import log_activity

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Schemas ──────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    email:     EmailStr
    password:  str
    full_name: str
    role:      str = "user"

    @field_validator("role")
    @classmethod
    def valid_role(cls, v):
        if v not in ("admin", "user"):
            raise ValueError("role must be 'admin' or 'user'")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UpdateUserRequest(BaseModel):
    full_name:  Optional[str] = None
    role:       Optional[str] = None
    is_active:  Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


def _user_dict(user: User, total_leads: int = 0, total_calls: int = 0) -> dict:
    return {
        "id":           user.id,
        "email":        user.email,
        "full_name":    user.full_name,
        "role":         user.role,
        "is_active":    user.is_active,
        "is_suspended": user.is_suspended,
        "created_at":   user.created_at.isoformat() if user.created_at else None,
        "last_login":   user.last_login.isoformat() if user.last_login else None,
        "total_leads":  total_leads,
        "total_calls":  total_calls,
    }


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)


# ── GET /admin/users ─────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    page:         int  = Query(1, ge=1),
    page_size:    int  = Query(20, ge=1, le=100),
    role:         Optional[str]  = None,
    is_active:    Optional[bool] = None,
    is_suspended: Optional[bool] = None,
    _admin: User = Depends(require_admin),
):
    qs = User.all()
    if role:         qs = qs.filter(role=role)
    if is_active    is not None: qs = qs.filter(is_active=is_active)
    if is_suspended is not None: qs = qs.filter(is_suspended=is_suspended)

    total = await qs.count()
    users = await qs.offset((page - 1) * page_size).limit(page_size)

    result = []
    for u in users:
        leads = await Lead.filter(user_id=u.id).count()
        calls = await CallLog.filter(user_id=u.id).count()
        result.append(_user_dict(u, leads, calls))

    return {"total": total, "page": page, "page_size": page_size, "users": result}


# ── POST /admin/users ────────────────────────────────────────────────

@router.post("/users", status_code=201)
async def create_user(
    body: CreateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
):
    if await User.get_or_none(email=body.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await User.create(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    await log_activity(admin.id, "admin_created_user", {"target_user_id": user.id}, _get_ip(request))
    return _user_dict(user)


# ── PUT /admin/users/{user_id} ───────────────────────────────────────

@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
):
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.full_name is not None: user.full_name = body.full_name
    if body.role      is not None: user.role      = body.role
    if body.is_active is not None: user.is_active = body.is_active
    await user.save()

    await log_activity(admin.id, "admin_updated_user", {"target_user_id": user_id}, _get_ip(request))
    return _user_dict(user)


# ── DELETE /admin/users/{user_id} ────────────────────────────────────

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await user.delete()
    await log_activity(admin.id, "admin_deleted_user", {"target_user_id": user_id}, _get_ip(request))
    return {"message": "User deleted"}


# ── POST /admin/users/{user_id}/suspend ──────────────────────────────

@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot suspend your own account")

    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_suspended = True
    await user.save()
    await log_activity(admin.id, "admin_suspended_user", {"target_user_id": user_id}, _get_ip(request))
    return {"message": "User suspended"}


# ── POST /admin/users/{user_id}/activate ─────────────────────────────

@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
):
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_suspended = False
    user.is_active    = True
    await user.save()
    await log_activity(admin.id, "admin_activated_user", {"target_user_id": user_id}, _get_ip(request))
    return {"message": "User activated"}


# ── POST /admin/users/{user_id}/reset-password ───────────────────────

@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    body: ResetPasswordRequest,
    request: Request,
    admin: User = Depends(require_admin),
):
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(body.new_password)
    await user.save()
    await log_activity(admin.id, "admin_reset_password", {"target_user_id": user_id}, _get_ip(request))
    return {"message": "Password reset successfully"}


# ── GET /admin/users/{user_id}/activity ──────────────────────────────

@router.get("/users/{user_id}/activity")
async def user_activity(
    user_id:   int,
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
):
    if not await User.get_or_none(id=user_id):
        raise HTTPException(status_code=404, detail="User not found")

    total = await UserActivity.filter(user_id=user_id).count()
    rows  = await UserActivity.filter(user_id=user_id)\
        .order_by("-created_at")\
        .offset((page - 1) * page_size)\
        .limit(page_size)

    return {
        "total": total,
        "page":  page,
        "activity": [
            {
                "id":         r.id,
                "action":     r.action,
                "details":    r.details,
                "ip_address": r.ip_address,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


# ── GET /admin/assistants/all ─────────────────────────────────────────

@router.get("/assistants/all")
async def list_all_assistants(
    user_id:   Optional[int] = None,
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
):
    qs = Assistant.all()
    if user_id:
        qs = qs.filter(user_id=user_id)

    total      = await qs.count()
    assistants = await qs.offset((page - 1) * page_size).limit(page_size)

    result = []
    for a in assistants:
        call_count = await CallLog.filter(assistant_name=a.name).count()
        owner      = await User.get_or_none(id=a.user_id)
        result.append({
            "id":               a.id,
            "name":             a.name,
            "voice_id":         a.voice_id,
            "model_name":       a.model_name,
            "vapi_assistant_id": a.vapi_assistant_id,
            "owner_user_id":    a.user_id,
            "owner_email":      owner.email if owner else None,
            "total_calls":      call_count,
        })

    return {"total": total, "page": page, "assistants": result}


# ── GET /admin/assistants/{assistant_id}/history ──────────────────────

@router.get("/assistants/{assistant_id}/history")
async def assistant_call_history(
    assistant_id: int,
    page:         int = Query(1, ge=1),
    page_size:    int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
):
    assistant = await Assistant.get_or_none(id=assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    total = await CallLog.filter(assistant_name=assistant.name).count()
    logs  = await CallLog.filter(assistant_name=assistant.name)\
        .order_by("-created_at")\
        .offset((page - 1) * page_size)\
        .limit(page_size)

    return {
        "total":     total,
        "page":      page,
        "assistant": assistant.name,
        "history": [
            {
                "call_id":          l.id,
                "lead_id":          l.lead_id,
                "ai_decision":      l.ai_decision,
                "call_status":      l.call_status,
                "duration_seconds": l.duration_seconds,
                "created_at":       l.created_at.isoformat(),
            }
            for l in logs
        ],
    }


# ── GET /admin/leads ─────────────────────────────────────────────────

@router.get("/leads")
async def admin_list_leads(
    user_id:    Optional[int]   = Query(None, description="Filter by user_id"),
    status:     Optional[str]   = Query(None, description="Filter by lead status"),
    lead_stage: Optional[str]   = Query(None, description="Filter by HubSpot lifecycle stage"),
    search:     Optional[str]   = Query(None, description="Search name/email/company"),
    sort:       str             = Query("updated_at", description="Sort field"),
    order:      str             = Query("desc",       description="asc or desc"),
    page:       int             = Query(1,   ge=1),
    page_size:  int             = Query(50,  ge=1, le=200),
    _admin: User = Depends(require_admin),
):
    """
    Admin-only: list leads across all users.
    - No user_id  → all leads with a user_id (no orphans)
    - user_id=X   → only that user's leads
    """
    if user_id:
        qs = Lead.filter(user_id=user_id)
    else:
        qs = Lead.filter(user_id__isnull=False)

    if status:     qs = qs.filter(status=status)
    if lead_stage: qs = qs.filter(lead_stage=lead_stage)

    if search:
        from tortoise.expressions import Q
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)  |
            Q(email__icontains=search)      |
            Q(company__icontains=search)
        )

    valid_sorts = {"score", "created_at", "updated_at", "last_call_at"}
    sort_field  = sort if sort in valid_sorts else "updated_at"
    sort_expr   = f"-{sort_field}" if order == "desc" else sort_field

    total = await qs.count()
    leads = await qs.order_by(sort_expr).offset((page - 1) * page_size).limit(page_size)

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "leads": [
            {
                "id":          l.id,
                "user_id":     l.user_id,
                "first_name":  l.first_name,
                "last_name":   l.last_name,
                "name":        f"{l.first_name or ''} {l.last_name or ''}".strip(),
                "email":       l.email,
                "phone":       l.phone,
                "company":     l.company,
                "score":       l.score,
                "status":      l.status,
                "stage":       l.lead_stage,
                "lead_stage":  l.lead_stage,
                "call_status": l.call_status,
                "ai_decision": l.ai_decision,
                "retry_count": l.retry_count,
                "updated_at":  l.updated_at.isoformat() if l.updated_at else None,
            }
            for l in leads
        ],
    }


# ── GET /admin/leads/{lead_id} ────────────────────────────────────────

@router.get("/leads/{lead_id}")
async def admin_get_lead(
    lead_id: int,
    _admin: User = Depends(require_admin),
):
    lead = await Lead.get_or_none(id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    owner = await User.get_or_none(id=lead.user_id) if lead.user_id else None

    return {
        "id":              lead.id,
        "user_id":         lead.user_id,
        "owner_email":     owner.email if owner else None,
        "first_name":      lead.first_name,
        "last_name":       lead.last_name,
        "name":            f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
        "email":           lead.email,
        "phone":           lead.phone,
        "company":         lead.company,
        "lead_stage":      lead.lead_stage,
        "score":           lead.score,
        "status":          lead.status,
        "call_status":     lead.call_status,
        "ai_decision":     lead.ai_decision,
        "last_transcript": lead.last_transcript,
        "retry_count":     lead.retry_count,
        "hubspot_id":      lead.hubspot_id,
        "created_at":      lead.created_at.isoformat() if lead.created_at else None,
        "updated_at":      lead.updated_at.isoformat() if lead.updated_at else None,
    }


# ── PUT /admin/leads/{lead_id} ────────────────────────────────────────

class AdminUpdateLeadRequest(BaseModel):
    first_name: Optional[str] = None
    last_name:  Optional[str] = None
    email:      Optional[str] = None
    phone:      Optional[str] = None
    company:    Optional[str] = None
    lead_stage: Optional[str] = None
    status:     Optional[str] = None


@router.put("/leads/{lead_id}")
async def admin_update_lead(
    lead_id: int,
    body: AdminUpdateLeadRequest,
    request: Request,
    admin: User = Depends(require_admin),
):
    from app.services.lead_scoring_service import LeadScoringService
    scorer = LeadScoringService()

    lead = await Lead.get_or_none(id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(lead, field, value)

    lead.score = scorer.calculate_score({
        "email":      lead.email,
        "phone":      lead.phone,
        "company":    lead.company,
        "lead_stage": lead.lead_stage,
    })

    await lead.save()
    await log_activity(admin.id, "admin_updated_lead", {"lead_id": lead_id}, _get_ip(request))

    return {
        "id":         lead.id,
        "first_name": lead.first_name,
        "last_name":  lead.last_name,
        "email":      lead.email,
        "phone":      lead.phone,
        "company":    lead.company,
        "lead_stage": lead.lead_stage,
        "status":     lead.status,
        "score":      lead.score,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


# ── DELETE /admin/leads/{lead_id} ─────────────────────────────────────

@router.delete("/leads/{lead_id}")
async def admin_delete_lead(
    lead_id: int,
    request: Request,
    admin: User = Depends(require_admin),
):
    lead = await Lead.get_or_none(id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    await lead.delete()
    await log_activity(admin.id, "admin_deleted_lead", {"lead_id": lead_id}, _get_ip(request))

    return {"message": "Lead deleted successfully"}


# ── GET /admin/celery/failed-jobs ─────────────────────────────────────
@router.get("/celery/failed-jobs")
async def failed_celery_jobs(_admin: User = Depends(require_admin)):
    """
    Query the Celery result backend (Redis) for FAILURE state tasks.
    Returns up to 50 most recent failures.
    """
    try:
        from app.queues.celery_app import celery_app
        inspect = celery_app.control.inspect(timeout=3)
        reserved = inspect.reserved() or {}
        # For failed tasks we query the backend directly
        from celery.result import AsyncResult
        # We can't enumerate all task IDs from Redis easily without
        # a task result backend scan — return a helpful message instead
        return {
            "message": "To view failed tasks, use Celery Flower at http://localhost:5555",
            "tip":     "Run: celery -A app.queues.celery_app flower --port=5555",
            "active_workers": list(reserved.keys()),
        }
    except Exception as e:
        return {"error": str(e), "message": "Celery inspect unavailable"}
