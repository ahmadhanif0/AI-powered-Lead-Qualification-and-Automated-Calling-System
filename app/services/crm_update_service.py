from app.crm.hubspot_client import HubSpotClient
from app.models.lead import Lead
from app.logs.logger import logger


# Map internal lead status values → HubSpot lifecyclestage values.
# HubSpot only accepts its own fixed lifecycle stage identifiers.
STATUS_TO_HUBSPOT_STAGE = {
    "Booked":            "opportunity",
    "Won't Follow Up":   "other",
    "Pending":           "lead",
    "Rejected":          "subscriber",
}


class CRMUpdateService:

    def __init__(self):
        # Do NOT instantiate HubSpotClient here — it requires a per-user
        # access token that isn't available at construction time.
        # All methods fetch the token lazily via HubSpotClient.for_user().
        pass

    async def _get_client_for_lead(self, lead: Lead):
        """
        Return a HubSpotClient for the user who owns this lead.
        Returns None (and logs a warning) if HubSpot is not connected.
        """
        if not lead.user_id:
            logger.warning(f"[CRM] Lead {lead.id} has no user_id — cannot get HubSpot client")
            return None
        try:
            from app.models.user import User
            user = await User.get_or_none(id=lead.user_id)
            if not user:
                logger.warning(f"[CRM] User {lead.user_id} not found for lead {lead.id}")
                return None
            return await HubSpotClient.for_user(user)
        except ValueError as e:
            # HubSpot not connected for this user — expected, non-fatal
            logger.info(f"[CRM] HubSpot not connected for user {lead.user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"[CRM] Failed to get HubSpot client for lead {lead.id}: {e}")
            return None

    # ------------------------------------------------------------------
    # Update HubSpot lifecycle stage
    # ------------------------------------------------------------------
    async def update_stage(self, lead_id: int, new_stage: str):
        lead = await Lead.get(id=lead_id)

        if not lead.hubspot_id:
            logger.warning(f"[CRM] Lead {lead_id} has no hubspot_id — skipping stage update")
            return

        client = await self._get_client_for_lead(lead)
        if not client:
            return

        try:
            raw_hs_id = lead.hubspot_id.split("_", 1)[-1]
            await client.update_contact_stage(contact_id=raw_hs_id, stage=new_stage)
            logger.info(f"[CRM] Stage updated for lead {lead_id}: {new_stage}")
        except Exception as e:
            logger.error(f"[CRM] Stage update failed for lead {lead_id}: {e}")
        # NOTE: we do NOT touch lead.lead_stage here — that field is managed
        # by the workflow engine, not by HubSpot stage strings.

    # ------------------------------------------------------------------
    # Sync internal status → HubSpot lifecycle stage
    # ------------------------------------------------------------------
    async def update_lead_status_in_crm(self, lead_id: int, status: str):
        """
        Map an internal status value to a HubSpot lifecycle stage and push.
        Logs a warning and returns gracefully if not connected or no mapping.
        """
        hubspot_stage = STATUS_TO_HUBSPOT_STAGE.get(status)
        if not hubspot_stage:
            logger.warning(
                f"[CRM] No HubSpot stage mapping for status '{status}' "
                f"(lead {lead_id}) — skipping"
            )
            return

        lead = await Lead.get(id=lead_id)

        if not lead.hubspot_id:
            logger.warning(f"[CRM] Lead {lead_id} has no hubspot_id — skipping status sync")
            return

        client = await self._get_client_for_lead(lead)
        if not client:
            return

        try:
            raw_hs_id = lead.hubspot_id.split("_", 1)[-1]
            await client.update_contact_stage(contact_id=raw_hs_id, stage=hubspot_stage)
            logger.info(
                f"[CRM] Status synced for lead {lead_id}: "
                f"'{status}' → HubSpot stage '{hubspot_stage}'"
            )
        except Exception as e:
            logger.error(f"[CRM] Status sync failed for lead {lead_id}: {e}")
