from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.user_crm import UserCRM
from app.crm.hubspot_client import HubSpotClient
from app.crm.hubspot_service import HubSpotService
from app.services.lead_sync_service import LeadSyncService
from app.queues.tasks import sync_hubspot_leads_task
from app.services.activity_logger import log_activity
from app.logs.logger import logger

router = APIRouter(prefix="/hubspot", tags=["HubSpot"])


async def _get_user_hubspot_service(user: User) -> HubSpotService:
    """
    Build a HubSpotService using the current user's OAuth token.
    Raises 400 if the user has not connected HubSpot.
    """
    try:
        client = await HubSpotClient.for_user(user)
        return HubSpotService(client=client)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e) + " — go to Settings → HubSpot to connect your account.",
        )


@router.get("/contacts")
async def get_hubspot_contacts(current_user: User = Depends(get_current_user)):
    """Preview HubSpot contacts using the current user's OAuth token."""
    logger.info(f"[HubSpot] Fetching contacts preview for user_id={current_user.id}")
    service  = await _get_user_hubspot_service(current_user)
    contacts = await service.fetch_contacts()
    logger.info(f"[HubSpot] Fetched {len(contacts)} contacts for user_id={current_user.id}")
    return {"total": len(contacts), "contacts": contacts}


@router.post("/sync")
async def sync_hubspot_contacts(current_user: User = Depends(get_current_user)):
    """Sync HubSpot contacts to leads (synchronous, waits for completion)."""
    logger.info(f"[HubSpot] Sync started for user_id={current_user.id} ({current_user.email})")

    # Build the service once and inject it — avoids building the OAuth client twice
    hs_service = await _get_user_hubspot_service(current_user)

    service = LeadSyncService(hubspot_service=hs_service)
    result  = await service.sync_hubspot_leads(user_id=current_user.id)

    logger.info(
        f"[HubSpot] Sync complete for user_id={current_user.id} — "
        f"total={result['total_contacts']}, created={result['created']}, "
        f"updated={result['updated']}, errors={result['errors']}"
    )

    # Update last_sync_at
    user_crm = await UserCRM.get_or_none(user_id=current_user.id, crm_type="hubspot")
    if user_crm:
        user_crm.last_sync_at = datetime.now(timezone.utc)
        await user_crm.save()

    await log_activity(current_user.id, "sync_crm", result)
    return result


@router.post("/sync-async")
async def sync_hubspot_async(current_user: User = Depends(get_current_user)):
    """Queue a background HubSpot sync via Celery."""
    logger.info(f"[HubSpot] Async sync queued for user_id={current_user.id}")

    # Verify connection before queuing
    await _get_user_hubspot_service(current_user)

    task = sync_hubspot_leads_task.delay(current_user.id)
    await log_activity(current_user.id, "sync_crm_async", {"task_id": task.id})
    return {"message": "Sync started in background", "task_id": task.id}
