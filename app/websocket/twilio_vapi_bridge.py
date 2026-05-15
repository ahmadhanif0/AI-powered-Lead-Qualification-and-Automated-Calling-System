import asyncio
import json
import httpx
from fastapi import WebSocket
from app.core.config import settings
from app.logs.logger import logger


class TwilioVapiBridge:
    
    def __init__(self):
        self.twilio_ws = None
        self.stream_sid = None
        self.call_sid = None
        self.vapi_call_id = None
        self.assistant_id = None
        
    async def initiate_vapi_call(self, phone_number: str, assistant_id: str, metadata: dict = None):
        """Start VAPI call via API"""
        
        payload = {
            "assistantId": assistant_id,
            "customer": {
                "number": phone_number
            },
            "metadata": metadata or {}
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.vapi.ai/call/phone",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {settings.VAPI_API_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                
                logger.info(f"VAPI call API status: {response.status_code}")
                logger.info(f"VAPI call API response: {response.text}")
                
                if response.status_code == 201:
                    result = response.json()
                    self.vapi_call_id = result.get("id")
                    logger.info(f"VAPI call initiated: {self.vapi_call_id}")
                    return result
                else:
                    logger.error(f"VAPI call failed: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"VAPI call API error: {str(e)}")
            return None
    
    async def handle_twilio_stream(self, websocket: WebSocket):
        """Handle Twilio media stream - just log for now"""
        
        self.twilio_ws = websocket
        await websocket.accept()
        
        logger.info("Twilio WebSocket connected")
        
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                event_type = message.get("event")
                
                if event_type == "start":
                    self.stream_sid = message["start"]["streamSid"]
                    self.call_sid = message["start"]["callSid"]
                    logger.info(f"Stream started - SID: {self.stream_sid}, Call: {self.call_sid}")
                    
                elif event_type == "media":
                    # Audio data from Twilio
                    pass
                    
                elif event_type == "stop":
                    logger.info("Twilio stream stopped")
                    break
                    
        except Exception as e:
            logger.error(f"Twilio stream error: {str(e)}")