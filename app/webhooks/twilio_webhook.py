from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from app.websocket.manager import manager
from app.websocket.twilio_vapi_bridge import TwilioVapiBridge
from app.repositories.lead_repository import LeadRepository
from app.core.config import settings
from app.logs.logger import logger

router = APIRouter()


@router.post("/twilio/voice")
async def twilio_voice(request: Request):

    data = await request.form()
    call_sid = data.get("CallSid")
    from_number = data.get("From")
    to_number = data.get("To")
    
    logger.info(f"Incoming call - CallSid: {call_sid}, From: {from_number}, To: {to_number}")
    
    # Extract lead_id from custom parameters if passed
    lead_id = data.get("lead_id")
    
    logger.info(f"Lead ID from request: {lead_id}")

    await manager.broadcast({
        "event": "call_started",
        "call_sid": call_sid,
        "lead_id": lead_id
    })

    # Get the host from request
    host = request.headers.get('host')
    
    # Build WebSocket URL
    ws_url = f"wss://{host}/ws/twilio-media/{lead_id or 'unknown'}"
    
    logger.info(f"WebSocket URL: {ws_url}")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Please wait while we connect you.</Say>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>
"""

    return Response(content=twiml, media_type="text/xml")


@router.websocket("/ws/twilio-media/{lead_id}")
async def twilio_media_stream(websocket: WebSocket, lead_id: str):
    """WebSocket endpoint for Twilio media stream"""
    
    logger.info(f"WebSocket connection attempt for lead: {lead_id}")
    
    bridge = None
    
    try:
        # Get lead with assistant
        lead_repo = LeadRepository()
        
        assistant_id = None
        
        if lead_id != "unknown":
            lead = await lead_repo.get_by_id_with_assistant(int(lead_id))
            
            if lead:
                logger.info(f"Lead found: {lead.id}")
                
                if lead.assistant:
                    logger.info(f"Assistant assigned: {lead.assistant.name}")
                    
                    if lead.assistant.vapi_assistant_id:
                        assistant_id = lead.assistant.vapi_assistant_id
                        logger.info(f"Using VAPI assistant: {assistant_id}")
                    else:
                        logger.warning("Assistant has no vapi_assistant_id")
                else:
                    logger.warning("No assistant assigned to lead")
        
        # Fallback to default assistant
        if not assistant_id:
            assistant_id = settings.VAPI_ASSISTANT_ID
            logger.info(f"Using default VAPI assistant: {assistant_id}")
        
        # Metadata for VAPI
        metadata = {
            "lead_id": lead_id
        }
        
        # Start bridge
        bridge = TwilioVapiBridge()
        await bridge.start_bridge(websocket, assistant_id, metadata)
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
    finally:
        if bridge and bridge.vapi_ws:
            try:
                await bridge.vapi_ws.close()
            except:
                pass
        try:
            await websocket.close()
        except:
            pass