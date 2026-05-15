from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.post("/twilio/voice")
async def twilio_voice():

    twiml = """
    <Response>
        <Say voice="alice">
            Hello, this is Cyberify AI calling.
        </Say>

        <Pause length="1"/>

        <Say>
            Connecting you to our AI assistant.
        </Say>
    </Response>
    """

    return Response(content=twiml, media_type="application/xml")