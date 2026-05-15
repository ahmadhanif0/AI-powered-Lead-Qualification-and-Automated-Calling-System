from datetime import datetime, timezone, timedelta

from app.ai.vapi_client import VapiClient
from app.repositories.lead_repository import LeadRepository
from app.repositories.call_log_repository import CallLogRepository
from app.services.assistant_service import AssistantService
from app.services.assistant_router import AssistantRouter
from app.core.config import settings
from app.websocket.manager import manager
from app.logs.logger import logger


class CallService:

    def __init__(self):
        self.vapi = VapiClient()
        self.lead_repo = LeadRepository()
        self.call_log_repo = CallLogRepository()
        self.assistant_service = AssistantService()
        self.router = AssistantRouter()

    async def start_call(self, lead_id: int, is_retry: bool = False):

        lead = await self.lead_repo.get_by_id(lead_id)

        if not lead:
            raise Exception("Lead not found")

        lead_data = {
            "id": lead.id,
            "phone": lead.phone,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "email": lead.email,
            "company": lead.company,
            "score": lead.score,
            "lead_stage": lead.lead_stage
        }

        # Prevent accidental duplicate calls from the UI (20-second window).
        # Intentional retries from the retry queue bypass this check entirely.
        if not is_retry and lead.last_call_at:
            diff = datetime.now(timezone.utc) - lead.last_call_at
            if diff < timedelta(seconds=20):
                raise Exception("Lead was already contacted recently")

        assistant = await self.router.select_assistant(lead_data)
        
        # Link assistant to lead
        await self.lead_repo.assign_assistant(
            lead_id=lead.id,
            assistant_id=assistant.id
        )
        
        # Convert assistant to dict
        assistant_dict = {
            "vapi_assistant_id": assistant.vapi_assistant_id,
            "name": assistant.name
        }

        # USE VAPI to make the call (VAPI will use Twilio internally)
        vapi_response = await self.vapi.make_call(
            lead=lead_data,
            assistant=assistant_dict
        )
        
        vapi_call_id = vapi_response.get("id")
        if not vapi_call_id:
            logger.error("VAPI CALL ID missing from response")

        # update lead
        await self.lead_repo.update_call_status(
            lead_id=lead.id,
            status="calling",
            call_sid=vapi_call_id,
            provider="vapi"
        )

        # save log
        await self.call_log_repo.create_log({
            "lead_id": lead.id,
            "assistant_name": assistant.name,
            "call_status": "calling",
            "vapi_call_id": vapi_call_id,
            "twilio_number": self.vapi.get_twilio_number()
        })

        # websocket event
        await manager.broadcast({
            "event": "call_started",
            "lead_id": lead.id,
            "status": "calling",
            "provider": "vapi",
            "call_id": vapi_call_id
        })

        return {
            "status": "calling",
            "call_id": vapi_call_id
        }