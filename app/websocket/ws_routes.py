from fastapi import APIRouter, WebSocket
from app.websocket.manager import manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    print("WS CONNECTED")

    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()

            print("WS MESSAGE:", data)

            await manager.broadcast({
                "event": "message",
                "data": data
            })

    except Exception as e:
        print("WS ERROR:", e)
        manager.disconnect(websocket)