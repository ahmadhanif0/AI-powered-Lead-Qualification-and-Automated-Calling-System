from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.global_events import global_event_manager

router = APIRouter()

@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):

    await global_event_manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        global_event_manager.disconnect(websocket)