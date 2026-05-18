import asyncio
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

import httpx

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.user_crm import UserCRM
from app.services.activity_logger import log_activity
from app.logs.logger import logger

router = APIRouter(prefix="/crm", tags=["CRM"])

SUPPORTED_CRMS = {"hubspot", "pipedrive", "zoho"}


# ── Schemas ──────────────────────────────────────────────────────────

class ConnectCRMRequest(BaseModel):
    crm_type:   str
    api_key:    str
    api_secret: Optional[str] = None


def _crm_dict(c: UserCRM) -> dict:
    return {
        "id":           c.id,
        "crm_type":     c.crm_type,
        "is_connected": c.is_connected,
        "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
        "created_at":   c.created_at.isoformat() if c.created_at else None,
    }


async def _test_hubspot_connection(api_key: str) -> bool:
    """Verify HubSpot key by fetching 1 contact."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"limit": 1},
            )
        return r.status_code == 200
    except Exception:
        return False


async def _test_connection(crm_type: str, api_key: str) -> bool:
    if crm_type == "hubspot":
        return await _test_hubspot_connection(api_key)
    # Pipedrive / Zoho — placeholder (always pass for now)
    return True


# ── GET /crm/connections ─────────────────────────────────────────────

@router.get("/connections")
async def list_connections(current_user: User = Depends(get_current_user)):
    conns = await UserCRM.filter(user_id=current_user.id).all()
    return [_crm_dict(c) for c in conns]


# ── POST /crm/connect ────────────────────────────────────────────────

@router.post("/connect")
async def connect_crm(
    body: ConnectCRMRequest,
    current_user: User = Depends(get_current_user),
):
    if body.crm_type not in SUPPORTED_CRMS:
        raise HTTPException(status_code=400, detail=f"Unsupported CRM. Choose from: {SUPPORTED_CRMS}")

    # Test the connection before saving
    ok = await _test_connection(body.crm_type, body.api_key)
    if not ok:
        raise HTTPException(status_code=400, detail="Connection test failed — check your API key")

    # Upsert: one connection per CRM type per user
    existing = await UserCRM.get_or_none(user_id=current_user.id, crm_type=body.crm_type)
    if existing:
        existing.api_key      = body.api_key
        existing.api_secret   = body.api_secret
        existing.is_connected = True
        await existing.save()
        conn = existing
    else:
        conn = await UserCRM.create(
            user_id=current_user.id,
            crm_type=body.crm_type,
            api_key=body.api_key,
            api_secret=body.api_secret,
            is_connected=True,
        )

    await log_activity(current_user.id, "crm_connected", {"crm_type": body.crm_type})
    return {"message": "CRM connected successfully", "connection": _crm_dict(conn)}


# ── DELETE /crm/connections/{crm_id} ────────────────────────────────

@router.delete("/connections/{crm_id}")
async def disconnect_crm(
    crm_id: int,
    current_user: User = Depends(get_current_user),
):
    conn = await UserCRM.get_or_none(id=crm_id, user_id=current_user.id)
    if not conn:
        raise HTTPException(status_code=404, detail="CRM connection not found")

    await conn.delete()
    await log_activity(current_user.id, "crm_disconnected", {"crm_id": crm_id})
    return {"message": "CRM disconnected"}


# ── POST /crm/sync ───────────────────────────────────────────────────

@router.post("/sync")
async def sync_crm(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    conn = await UserCRM.get_or_none(user_id=current_user.id, is_connected=True)
    if not conn:
        raise HTTPException(status_code=400, detail="No connected CRM found. Connect a CRM first.")

    # Fire background sync using user's own API key
    background_tasks.add_task(_run_crm_sync, current_user.id, conn)
    await log_activity(current_user.id, "crm_sync_started", {"crm_type": conn.crm_type})

    return {"message": f"Sync started for {conn.crm_type}", "crm_id": conn.id}


async def _run_crm_sync(user_id: int, conn: UserCRM):
    """Background task: sync contacts using user's own CRM credentials."""
    try:
        from app.crm.hubspot_client import HubSpotClient
        from app.crm.hubspot_service import HubSpotService
        from app.services.lead_sync_service import LeadSyncService

        if conn.crm_type == "hubspot":
            # Temporarily override the client with user's key
            client  = HubSpotClient(api_key_override=conn.api_key)
            service = HubSpotService(client=client)
            sync    = LeadSyncService(hubspot_service=service)
            result  = await sync.sync_hubspot_leads(user_id=user_id)

            conn.last_sync_at = datetime.now(timezone.utc)
            await conn.save()

            logger.info(f"CRM sync complete for user {user_id}: {result}")

    except Exception as e:
        logger.error(f"CRM sync failed for user {user_id}: {e}")
