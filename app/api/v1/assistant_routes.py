from fastapi import APIRouter, HTTPException, Depends

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.assistant import Assistant
from app.services.assistant_service import AssistantService
from app.schemas.assistant_schema import CreateAssistantSchema
from app.services.activity_logger import log_activity
from app.ai.vapi_client import VapiClient
from app.logs.logger import logger

router = APIRouter(prefix="/assistants", tags=["Assistants"])


@router.post("/", status_code=201)
async def create_assistant(
    payload: CreateAssistantSchema,
    current_user: User = Depends(get_current_user),
):
    service   = AssistantService()
    assistant = await service.create_assistant(payload, user_id=current_user.id)

    await log_activity(current_user.id, "create_assistant", {"assistant_id": assistant.id})

    return {
        "message": "Assistant created successfully",
        "assistant": {
            "id":               assistant.id,
            "name":             assistant.name,
            "vapi_assistant_id": assistant.vapi_assistant_id,
        },
    }


@router.get("/")
async def list_assistants(current_user: User = Depends(get_current_user)):
    # Admins see all; regular users see only their own
    if current_user.role == "admin":
        assistants = await Assistant.all()
    else:
        assistants = await Assistant.filter(user_id=current_user.id)

    return {
        "total": len(assistants),
        "assistants": [
            {
                "id":               a.id,
                "name":             a.name,
                "voice_id":         a.voice_id,
                "model_name":       a.model_name,
                "model_provider":   a.model_provider,
                "vapi_assistant_id": a.vapi_assistant_id,
            }
            for a in assistants
        ],
    }


@router.get("/{assistant_id}")
async def get_assistant(
    assistant_id: int,
    current_user: User = Depends(get_current_user),
):
    assistant = await Assistant.get_or_none(id=assistant_id)

    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    # Ownership check
    if current_user.role != "admin" and assistant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id":               assistant.id,
        "name":             assistant.name,
        "system_prompt":    assistant.system_prompt,
        "first_message":    assistant.first_message,
        "voice_id":         assistant.voice_id,
        "model_provider":   assistant.model_provider,
        "model_name":       assistant.model_name,
        "vapi_assistant_id": assistant.vapi_assistant_id,
    }


@router.put("/{assistant_id}")
async def update_assistant(
    assistant_id: int,
    payload: CreateAssistantSchema,
    current_user: User = Depends(get_current_user),
):
    assistant = await Assistant.get_or_none(id=assistant_id)

    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    if current_user.role != "admin" and assistant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Sync to VAPI first — if VAPI fails, block the update so DB and VAPI stay in sync
    if assistant.vapi_assistant_id:
        try:
            vapi = VapiClient()
            await vapi.update_assistant(
                assistant.vapi_assistant_id,
                {
                    "name":           payload.name,
                    "system_prompt":  payload.system_prompt,
                    "first_message":  payload.first_message,
                    "voice_id":       payload.voice_id,
                    "model_provider": payload.model_provider,
                    "model_name":     payload.model_name,
                },
            )
            logger.info(f"Updated VAPI assistant {assistant.vapi_assistant_id}")
        except Exception as e:
            logger.error(f"Failed to update VAPI assistant {assistant.vapi_assistant_id}: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"VAPI update failed: {e}. Local database was NOT changed.",
            )

    # Update local DB only after VAPI succeeds
    assistant.name           = payload.name
    assistant.system_prompt  = payload.system_prompt
    assistant.first_message  = payload.first_message
    assistant.voice_id       = payload.voice_id
    assistant.model_provider = payload.model_provider
    assistant.model_name     = payload.model_name
    await assistant.save()

    await log_activity(
        current_user.id,
        "update_assistant",
        {"assistant_id": assistant_id, "name": assistant.name},
    )

    return {
        "id":               assistant.id,
        "name":             assistant.name,
        "system_prompt":    assistant.system_prompt,
        "first_message":    assistant.first_message,
        "voice_id":         assistant.voice_id,
        "model_provider":   assistant.model_provider,
        "model_name":       assistant.model_name,
        "vapi_assistant_id": assistant.vapi_assistant_id,
    }


@router.delete("/{assistant_id}")
async def delete_assistant(
    assistant_id: int,
    current_user: User = Depends(get_current_user),
):
    assistant = await Assistant.get_or_none(id=assistant_id)

    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    if current_user.role != "admin" and assistant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete from VAPI first — log but never block local deletion
    if assistant.vapi_assistant_id:
        try:
            vapi = VapiClient()
            await vapi.delete_assistant(assistant.vapi_assistant_id)
            logger.info(f"Deleted VAPI assistant {assistant.vapi_assistant_id} for local id {assistant_id}")
        except Exception as e:
            logger.error(
                f"Failed to delete assistant {assistant.vapi_assistant_id} from VAPI: {e} — "
                "continuing with local deletion"
            )

    # Always delete locally regardless of VAPI outcome
    await assistant.delete()
    await log_activity(
        current_user.id,
        "delete_assistant",
        {"assistant_id": assistant_id, "name": assistant.name, "vapi_id": assistant.vapi_assistant_id},
    )

    return {"message": "Assistant deleted successfully"}
