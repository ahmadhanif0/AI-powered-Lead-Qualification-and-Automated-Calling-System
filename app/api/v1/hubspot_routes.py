from fastapi import APIRouter

from app.crm.hubspot_service import HubSpotService
from app.services.lead_sync_service import LeadSyncService
from app.queues.tasks import sync_hubspot_leads_task


router = APIRouter(
    prefix="/hubspot",
    tags=["HubSpot"]
)


@router.get("/contacts")
async def get_hubspot_contacts():

    service = HubSpotService()

    contacts = await service.fetch_contacts()

    return {
        "total": len(contacts),
        "contacts": contacts
    }


@router.post("/sync")
async def sync_hubspot_contacts():

    service = LeadSyncService()

    result = await service.sync_hubspot_leads()

    return result

@router.post("/sync-async")
async def sync_hubspot_async():

    task = sync_hubspot_leads_task.delay()

    return {
        "message": "Sync started in background",
        "task_id": task.id
    }