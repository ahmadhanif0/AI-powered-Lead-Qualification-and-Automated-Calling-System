from app.crm.hubspot_service import HubSpotService
from app.repositories.lead_repository import LeadRepository
from app.services.lead_scoring_service import LeadScoringService
from app.api.v1.leads import infer_stage
from app.logs.logger import logger


class LeadSyncService:

    def __init__(self, hubspot_service: HubSpotService = None):
        self._hubspot_service = hubspot_service
        self.lead_repository  = LeadRepository()
        self.scoring_service  = LeadScoringService()

    async def sync_hubspot_leads(self, user_id: int = None):
        """
        Fetch contacts from HubSpot and upsert them as leads.
        user_id scopes all created leads to the triggering user.
        """
        # ── Build HubSpot service ────────────────────────────────────
        if self._hubspot_service is None:
            if user_id:
                try:
                    from app.models.user import User
                    from app.crm.hubspot_client import HubSpotClient
                    user   = await User.get(id=user_id)
                    client = await HubSpotClient.for_user(user)
                    hubspot_service = HubSpotService(client=client)
                    logger.info(f"[Sync] Built HubSpot client for user_id={user_id}")
                except Exception as e:
                    logger.error(f"[Sync] Cannot build HubSpot client for user {user_id}: {e}")
                    raise Exception(f"HubSpot not connected for user {user_id}: {e}")
            else:
                logger.warning("[Sync] No user_id provided — using legacy fallback client")
                hubspot_service = HubSpotService()
        else:
            hubspot_service = self._hubspot_service
            logger.info(f"[Sync] Using injected HubSpot service for user_id={user_id}")

        # ── Fetch contacts ───────────────────────────────────────────
        contacts = await hubspot_service.fetch_contacts()
        logger.info(f"[Sync] Fetched {len(contacts)} contacts from HubSpot for user_id={user_id}")

        created_count = 0
        updated_count = 0
        error_count   = 0

        for contact in contacts:
            hubspot_id = contact.get("id")
            try:
                properties = contact.get("properties", {})

                if not hubspot_id:
                    logger.warning(f"[Sync] Skipping contact with no id: {contact}")
                    error_count += 1
                    continue

                logger.debug(
                    f"[Sync] Processing contact id={hubspot_id} "
                    f"name={properties.get('firstname')} {properties.get('lastname')} "
                    f"email={properties.get('email')}"
                )

                lead_data = {
                    "first_name": properties.get("firstname"),
                    "last_name":  properties.get("lastname"),
                    "email":      properties.get("email"),
                    "phone":      properties.get("phone"),
                    "company":    properties.get("company"),
                    "lead_stage": infer_stage(
                        properties.get("email")      or "",
                        properties.get("phone")      or "",
                        properties.get("company")    or "",
                        properties.get("lifecyclestage") or None,
                    ),
                }

                score = self.scoring_service.calculate_score(lead_data)
                lead_data["score"] = score

                # Per-user scoped key prevents unique constraint clash when
                # two users sync the same HubSpot contact.
                # Format: "<user_id>_<hubspot_id>"
                scoped_hubspot_id       = f"{user_id}_{hubspot_id}" if user_id else hubspot_id
                lead_data["hubspot_id"] = scoped_hubspot_id

                existing_lead = await self.lead_repository.get_by_hubspot_id(
                    scoped_hubspot_id, user_id=user_id
                )

                if existing_lead:
                    await self.lead_repository.update_lead(existing_lead, lead_data)
                    updated_count += 1
                    logger.debug(f"[Sync] Updated existing lead id={existing_lead.id} (hubspot={scoped_hubspot_id})")
                else:
                    lead_data["user_id"] = user_id   # always set — user_id is required
                    new_lead = await self.lead_repository.create_lead(lead_data)
                    created_count += 1
                    logger.info(
                        f"[Sync] Created lead id={new_lead.id} "
                        f"name={new_lead.first_name} {new_lead.last_name} "
                        f"user_id={new_lead.user_id} score={score}"
                    )

                    if score >= 50:
                        from app.queues.tasks import start_lead_call_task
                        start_lead_call_task.delay(new_lead.id)
                        logger.info(f"[Sync] Auto-call queued for lead id={new_lead.id} (score={score})")

            except Exception as e:
                error_count += 1
                logger.error(
                    f"[Sync] ERROR processing contact id={hubspot_id}: {type(e).__name__}: {e}",
                    exc_info=True,
                )
                continue

        logger.info(
            f"[Sync] COMPLETE for user_id={user_id} — "
            f"total={len(contacts)}, created={created_count}, "
            f"updated={updated_count}, errors={error_count}"
        )

        return {
            "total_contacts": len(contacts),
            "created":  created_count,
            "updated":  updated_count,
            "errors":   error_count,
        }
