from app.crm.hubspot_service import HubSpotService
from app.repositories.lead_repository import LeadRepository
from app.services.lead_scoring_service import LeadScoringService
from app.logs.logger import logger


class LeadSyncService:

    def __init__(self):
        self.hubspot_service = HubSpotService()
        self.lead_repository = LeadRepository()
        self.scoring_service = LeadScoringService()

    async def sync_hubspot_leads(self):

        contacts = await self.hubspot_service.fetch_contacts()

        created_count = 0
        updated_count = 0
        error_count   = 0

        for contact in contacts:

            # --------------------------------------------------
            # Per-contact error isolation: a bad record (missing
            # hubspot_id, DB constraint, etc.) is logged and
            # skipped so the rest of the sync continues.
            # --------------------------------------------------
            try:
                properties = contact.get("properties", {})
                hubspot_id = contact.get("id")

                if not hubspot_id:
                    logger.warning(
                        f"Skipping contact with no id: {contact}"
                    )
                    error_count += 1
                    continue

                lead_data = {
                    "hubspot_id": hubspot_id,
                    "first_name": properties.get("firstname"),
                    "last_name":  properties.get("lastname"),
                    "email":      properties.get("email"),
                    "phone":      properties.get("phone"),
                    "company":    properties.get("company"),
                    "lead_stage": properties.get("lifecyclestage"),
                }

                score = self.scoring_service.calculate_score(lead_data)
                lead_data["score"] = score

                existing_lead = await self.lead_repository.get_by_hubspot_id(
                    hubspot_id=hubspot_id
                )

                if existing_lead:
                    await self.lead_repository.update_lead(
                        lead=existing_lead,
                        data=lead_data
                    )
                    updated_count += 1

                else:
                    new_lead = await self.lead_repository.create_lead(
                        data=lead_data
                    )
                    created_count += 1

                    if score >= 50:
                        from app.queues.tasks import start_lead_call_task
                        start_lead_call_task.delay(new_lead.id)

            except Exception as e:
                error_count += 1
                logger.error(
                    f"Error syncing contact {contact.get('id', 'unknown')}: "
                    f"{e}"
                )
                # Continue with the next contact
                continue

        logger.info(
            f"Sync complete — created: {created_count}, "
            f"updated: {updated_count}, errors: {error_count}"
        )

        return {
            "total_contacts": len(contacts),
            "created":  created_count,
            "updated":  updated_count,
            "errors":   error_count,
        }
