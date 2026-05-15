from twilio.rest import Client
from app.core.config import settings
from urllib.parse import urlencode


class TwilioClient:

    def __init__(self):
        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )

    def make_call(self, to_number: str, webhook_url: str, lead_id: int = None):
        
        # Build URL with query parameters
        if lead_id:
            params = urlencode({"lead_id": lead_id})
            full_webhook_url = f"{webhook_url}?{params}"
        else:
            full_webhook_url = webhook_url

        call = self.client.calls.create(
            to=to_number,
            from_=self.get_active_number(),
            url=full_webhook_url
        )

        return call.sid

    def get_active_number(self):
        numbers = self.client.incoming_phone_numbers.list(limit=1)
        return numbers[0].phone_number