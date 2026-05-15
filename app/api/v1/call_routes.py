from fastapi import APIRouter

from app.ai.call_service import CallService

router = APIRouter(
    prefix="/calls",
    tags=["Calls"]
)

service = CallService()


@router.post("/start/{lead_id}")
async def start_call(lead_id: int):

    result = await service.start_call(lead_id)

    return {
        "message": "Call started successfully",
        "result": result
    }