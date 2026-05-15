from app.models.assistant import Assistant
from app.ai.vapi_client import VapiClient


class AssistantService:

    def __init__(self):

        self.vapi = VapiClient()

    async def create_assistant(self, data):
        # 1. Create in Vapi
        vapi_assistant = (
            await self.vapi.create_assistant(data)
        )

        # 2. Save locally
        assistant = await Assistant.create(
            name=data.name,
            system_prompt=data.system_prompt,
            first_message=data.first_message,
            voice_id=data.voice_id,
            model_provider=data.model_provider,
            model_name=data.model_name,
            vapi_assistant_id=vapi_assistant["id"]
        )

        return assistant

    async def get_assistant(self, assistant_id: int):

        return await Assistant.get(id=assistant_id)

    async def list_assistants(self):

        return await Assistant.all()