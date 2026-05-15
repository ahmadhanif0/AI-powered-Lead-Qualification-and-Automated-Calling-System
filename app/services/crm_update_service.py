from app.crm.hubspot_client import HubSpotClient
from app.models.lead import Lead
from app.logs.logger import logger


# Map internal lead status values → HubSpot lifecyclestage values.
# HubSpot only accepts its own fixed lifecycle stage identifiers.
STATUS_TO_HUBSPOT_STAGE = {
    "Booked":            "opportunity",   # Interested
    "Won't Follow Up":   "other",         # Not Interested
    "Pending":           "lead",          # Call Later
    "Rejected":          "subscriber",    # Wrong Number / No Response
}


class CRMUpdateService:

    def __init__(self):
        self.client = HubSpotClient()

    # ------------------------------------------------------------------
    # Update HubSpot lifecycle stage (existing method — unchanged callers)
    # ------------------------------------------------------------------
    async def update_stage(
        self,
        lead_id: int,
        new_stage: str
    ):
        lead = await Lead.get(id=lead_id)

        if not lead.hubspot_id:
            logger.warning(
                f"Lead {lead_id} has no hubspot_id — skipping CRM stage update"
            )
            return

        await self.client.update_contact_stage(
            contact_id=lead.hubspot_id,
            stage=new_stage
        )

        lead.lead_stage = new_stage
        await lead.save()

        logger.info(
            f"CRM stage updated for lead {lead_id}: {new_stage}"
        )

    # ------------------------------------------------------------------
    # NEW: Sync internal status → HubSpot lifecycle stage.
    # Called from every workflow action handler after status is set.
    # ------------------------------------------------------------------
    async def update_lead_status_in_crm(
        self,
        lead_id: int,
        status: str
    ):
        """
        Map an internal status value to a HubSpot lifecycle stage and
        push the update.  Logs a warning and returns gracefully if the
        lead has no hubspot_id or the status has no mapping.
        """
        hubspot_stage = STATUS_TO_HUBSPOT_STAGE.get(status)

        if not hubspot_stage:
            logger.warning(
                f"No HubSpot stage mapping for status '{status}' "
                f"(lead {lead_id}) — skipping CRM status sync"
            )
            return

        lead = await Lead.get(id=lead_id)

        if not lead.hubspot_id:
            logger.warning(
                f"Lead {lead_id} has no hubspot_id — skipping CRM status sync"
            )
            return

        try:
            await self.client.update_contact_stage(
                contact_id=lead.hubspot_id,
                stage=hubspot_stage
            )

            lead.lead_stage = hubspot_stage
            await lead.save()

            logger.info(
                f"CRM status synced for lead {lead_id}: "
                f"'{status}' → HubSpot stage '{hubspot_stage}'"
            )

        except Exception as e:
            # Never let a CRM sync failure break the workflow
            logger.error(
                f"CRM status sync failed for lead {lead_id} "
                f"(status='{status}'): {e}"
            )
