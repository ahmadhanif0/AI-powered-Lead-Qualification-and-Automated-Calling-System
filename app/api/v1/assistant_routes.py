from fastapi import APIRouter, HTTPException

from app.services.assistant_service import AssistantService
from app.schemas.assistant_schema import CreateAssistantSchema
router = APIRouter(
    prefix="/assistants",
    tags=["Assistants"]
)

service = AssistantService()

@router.post("/")
async def create_assistant(payload: CreateAssistantSchema):
    assistant = await service.create_assistant(payload)

    return {
        "message": "Assistant created successfully",
        "assistant": {
            "id": assistant.id,
            "name": assistant.name,
            "vapi_assistant_id": (
                assistant.vapi_assistant_id
            )
        }
    }


@router.get("/{assistant_id}")
async def get_assistant(assistant_id: int):

    assistant = await service.get_assistant(assistant_id)

    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    return {
        "id": assistant.id,
        "name": assistant.name,
        "system_prompt": assistant.system_prompt,
        "first_message": assistant.first_message,
        "voice_id": assistant.voice_id,
        "model_provider": assistant.model_provider,
        "model_name": assistant.model_name,
        "vapi_assistant_id": (
            assistant.vapi_assistant_id
        )
    }


@router.get("/")
async def list_assistants():

    assistants = await service.list_assistants()

    return {
        "total": len(assistants),

        "assistants": [
            {
                "id": assistant.id,
                "name": assistant.name,
                "voice_id": assistant.voice_id,
                "model_name": assistant.model_name,
                "vapi_assistant_id": (
                    assistant.vapi_assistant_id
                )
            }
            for assistant in assistants
        ]
    }