from app.models.assistant import Assistant
from app.ai.vapi_client import VapiClient


class AssistantService:

    def __init__(self):
        self.vapi = VapiClient()

    async def create_assistant(self, data, user_id: int = None):
        # 1. Create in VAPI
        vapi_assistant = await self.vapi.create_assistant(data)

        # 2. Save locally, scoped to the user
        assistant = await Assistant.create(
            name=data.name,
            system_prompt=data.system_prompt,
            first_message=data.first_message,
            voice_id=data.voice_id,
            model_provider=data.model_provider,
            model_name=data.model_name,
            vapi_assistant_id=vapi_assistant["id"],
            user_id=user_id,
        )
        return assistant

    async def get_assistant(self, assistant_id: int):
        return await Assistant.get_or_none(id=assistant_id)

    async def list_assistants(self, user_id: int = None):
        if user_id is None:
            return await Assistant.all()
        return await Assistant.filter(user_id=user_id)
