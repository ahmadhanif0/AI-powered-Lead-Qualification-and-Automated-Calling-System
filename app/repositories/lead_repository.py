from typing import Optional
from datetime import datetime, timezone

from app.models.lead import Lead
from app.models.assistant import Assistant


class LeadRepository:

    @staticmethod
    async def get_by_hubspot_id(
        hubspot_id: str,
        user_id: int = None,
    ) -> Optional[Lead]:
        """
        Find a lead by HubSpot contact ID.
        When user_id is provided, scope to that user so two users
        can each have the same HubSpot contact as separate leads.
        """
        qs = Lead.filter(hubspot_id=hubspot_id)
        if user_id is not None:
            qs = qs.filter(user_id=user_id)
        return await qs.first()


    @staticmethod
    async def create_lead(data: dict) -> Lead:

        return await Lead.create(
            hubspot_id=data["hubspot_id"],
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            company=data.get("company"),
            lead_stage=data.get("lead_stage"),
            score=data.get("score", 0),
            user_id=data.get("user_id"),   # multi-tenant: scope lead to its owner
        )
    
    @staticmethod
    async def update_lead(lead: Lead, data: dict) -> Lead:

        lead.first_name = data.get("first_name")
        lead.last_name = data.get("last_name")
        lead.email = data.get("email")
        lead.phone = data.get("phone")
        lead.company = data.get("company")
        lead.lead_stage = data.get("lead_stage")
        lead.score = data.get("score", lead.score)

        await lead.save()

        return lead
    
    @staticmethod
    async def update_lead_status(lead_id: int, status: str):

        lead = await Lead.get(id=lead_id)

        lead.status = status

        await lead.save()

        return lead
    
    @staticmethod
    async def get_by_id(lead_id: int):

        return await Lead.get_or_none(id=lead_id)
    
    @staticmethod
    async def get_by_id_with_assistant(lead_id: int):
        """Get lead with assistant data preloaded"""
        return await Lead.get_or_none(id=lead_id).prefetch_related('assistant')
    
    async def update_call_status(self, lead_id: int, status: str, call_sid: str = None, provider: str = None):

        lead = await Lead.get(id=lead_id)

        lead.call_status = status
        lead.last_call_at = datetime.now(timezone.utc)

        if call_sid:
            lead.call_sid = call_sid

        if provider:
            lead.call_provider = provider

        await lead.save()

        return lead


    @staticmethod
    async def save_transcript_and_decision(
        lead_id: int,
        transcript: str,
        decision: str
    ):

        lead = await Lead.get(id=lead_id)

        lead.last_transcript = transcript
        lead.ai_decision = decision

        await lead.save()

        return lead
    
    @staticmethod
    async def update_retry_info(
        lead_id: int,
        retry_count: int,
        next_retry_at,
        status: str
    ):

        lead = await Lead.get(id=lead_id)

        lead.retry_count = retry_count
        lead.next_retry_at = next_retry_at
        lead.status = status

        await lead.save()

        return lead
    

    @staticmethod
    async def update_lead_score(
        lead_id: int,
        ai_score: float
    ):

        lead = await Lead.get(id=lead_id)

        lead.score += ai_score

        # clamp final score
        lead.score = max(
            min(lead.score, 100),
            0
        )

        await lead.save()

        return lead
    
    @staticmethod
    async def assign_assistant(lead_id: int, assistant_id: int):
        """Link vapi assistant to lead for the call"""
        lead = await Lead.get(id=lead_id)
        assistant = await Assistant.get(id=assistant_id)
        
        if lead and assistant:
            lead.assistant = assistant
            await lead.save()
        
        return lead