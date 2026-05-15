# import httpx

# from app.core.config import settings
# from app.logs.logger import logger
# from twilio.rest import Client


# class VapiClient:

#     BASE_URL = "https://api.vapi.ai"

#     def __init__(self):
#         self.twilio = Client(
#             settings.TWILIO_ACCOUNT_SID,
#             settings.TWILIO_AUTH_TOKEN
#         )

#     def get_twilio_number(self):
#         numbers = self.twilio.incoming_phone_numbers.list()

#         if not numbers:
#             raise Exception("No Twilio numbers found")

#         return numbers[0].phone_number

#     # ==========================================
#     # FORMAT PHONE
#     # ==========================================
#     def _format_phone(self, phone: str):

#         if not phone:
#             return None

#         phone = (
#             phone
#             .replace(" ", "")
#             .replace("-", "")
#         )

#         if phone.startswith("0"):
#             phone = "+92" + phone.lstrip("0")

#         if not phone.startswith("+"):
#             phone = "+92" + phone

#         return phone

#     # ==========================================
#     # START CALL
#     # ==========================================
#     async def make_call(
#         self,
#         lead: dict,
#         assistant: dict
#     ):

#         logger.info(f"Lead Data: {lead}")
#         logger.info(
#             f"Phone Value: {lead.get('phone')}"
#         )

#         # -------------------------
#         # FORMAT PHONE
#         # -------------------------
#         phone = self._format_phone(
#             lead.get("phone")
#         )

#         if not phone:
#             raise Exception(
#                 "Lead phone is missing or invalid"
#             )

#         # -------------------------
#         # VALIDATE ASSISTANT
#         # -------------------------
#         vapi_assistant_id = assistant.get(
#             "vapi_assistant_id"
#         )

#         if not vapi_assistant_id:
#             raise Exception(
#                 "Vapi assistant ID missing"
#             )

#         # -------------------------
#         # BUILD PAYLOAD
#         # -------------------------
#         twilio_number = self.get_twilio_number()

#         # payload = {
#         #     "assistant": {
#         #         "name": assistant.get("name"),
#         #         "firstMessage": assistant.get("first_message"),
#         #         "model": {
#         #             "provider": "openai",
#         #             "model": "gpt-4.1",
#         #             "messages": [
#         #                 {
#         #                     "role": "system",
#         #                     "content": assistant.get("system_prompt")
#         #                 }
#         #             ]
#         #         },
#         #         "voice": {
#         #             "provider": "vapi",
#         #             "voiceId": assistant.get("voice_id", "Elliot")
#         #         }
#         #     },

#         #     "customer": {
#         #         "number": phone
#         #     },

#         #     "phoneNumber": {
#         #         "twilioAccountSid": settings.TWILIO_ACCOUNT_SID,
#         #         "twilioAuthToken": settings.TWILIO_AUTH_TOKEN,
#         #         "twilioPhoneNumber": twilio_number
#         #     }
#         # }

#         # payload = {
#         #     "assistantId": assistant["vapi_assistant_id"],

#         #     "customer": {
#         #         "number": phone
#         #     },

#         #     "phoneNumber": {
#         #         "twilioAccountSid": settings.TWILIO_ACCOUNT_SID,
#         #         "twilioAuthToken": settings.TWILIO_AUTH_TOKEN,
#         #         "twilioPhoneNumber": twilio_number
#         #     }
            
#         # }

#         payload = {
#             "assistantId": assistant["vapi_assistant_id"],

#             "phoneNumberId": settings.VAPI_PHONE_NUMBER_ID,

#             "customer": {
#                 "number": phone
#             },

#             "metadata": {
#                 "lead_id": str(lead["id"]),
#                 "lead_phone": phone,
#                 "assistant_name": assistant["name"]
#             }
#         }

#         logger.info(
#             f"Vapi Payload: {payload}"
#         )

#         print("DYNAMIC CALL PAYLOAD:")
#         print(payload)

#         # -------------------------
#         # API CALL
#         # -------------------------
#         try:

#             async with httpx.AsyncClient(
#                 timeout=30
#             ) as client:

#                 response = await client.post(
#                     f"{self.BASE_URL}/call/phone",

#                     json=payload,

#                     headers={
#                         "Authorization":
#                         (
#                             f"Bearer "
#                             f"{settings.VAPI_API_KEY}"
#                         ),

#                         "Content-Type":
#                         "application/json"
#                     }
#                 )

#             logger.info(
#                 f"Vapi Status: "
#                 f"{response.status_code}"
#             )

#             logger.info(
#                 f"Vapi Response: "
#                 f"{response.text}"
#             )

#             print(
#                 "VAPI STATUS:",
#                 response.status_code
#             )

#             print(
#                 "VAPI RESPONSE:",
#                 response.text
#             )

#             response.raise_for_status()

#             return response.json()

#         except Exception as e:

#             logger.error(
#                 f"Vapi Call Failed: {str(e)}"
#             )

#             try:
#                 error_text = response.text
#             except:
#                 error_text = str(e)

#             raise Exception(
#                 f"Vapi Response: {error_text}"
#             )

#     # ==========================================
#     # CREATE ASSISTANT
#     # ==========================================
#     async def create_assistant(self, data):

#         payload = {

#             "name": data.name,

#             "firstMessage": (
#                 data.first_message
#             ),

#             "model": {
#                 "provider":
#                 data.model_provider,

#                 "model":
#                 data.model_name,

#                 "messages": [
#                     {
#                         "role": "system",

#                         "content":
#                         data.system_prompt
#                     }
#                 ]
#             },

#             "voice": {
#                 "provider": "vapi",

#                 "voiceId":
#                 data.voice_id
#             }
#         }

#         logger.info(
#             f"Create Assistant Payload: "
#             f"{payload}"
#         )

#         async with httpx.AsyncClient(
#             timeout=30
#         ) as client:

#             response = await client.post(
#                 f"{self.BASE_URL}/assistant",

#                 json=payload,

#                 headers={
#                     "Authorization":
#                     (
#                         f"Bearer "
#                         f"{settings.VAPI_API_KEY}"
#                     ),

#                     "Content-Type":
#                     "application/json"
#                 }
#             )

#         print(
#             "VAPI ASSISTANT STATUS:",
#             response.status_code
#         )

#         print(
#             "VAPI ASSISTANT RESPONSE:",
#             response.text
#         )

#         logger.info(
#             f"Assistant Create Status: "
#             f"{response.status_code}"
#         )

#         logger.info(
#             f"Assistant Create Response: "
#             f"{response.text}"
#         )

#         response.raise_for_status()

#         return response.json()

import httpx
from app.core.config import settings
from app.logs.logger import logger
from twilio.rest import Client


class VapiClient:

    BASE_URL = "https://api.vapi.ai"

    def __init__(self):
        self.twilio = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )

    def get_twilio_number(self):
        numbers = self.twilio.incoming_phone_numbers.list()

        if not numbers:
            raise Exception("No Twilio numbers found")

        return numbers[0].phone_number

    def _format_phone(self, phone: str):
        if not phone:
            return None

        phone = phone.replace(" ", "").replace("-", "")

        if phone.startswith("0"):
            phone = "+92" + phone.lstrip("0")

        if not phone.startswith("+"):
            phone = "+92" + phone

        return phone

    async def make_call(self, lead: dict, assistant: dict):

        logger.info(f"Lead Data: {lead}")

        phone = self._format_phone(lead.get("phone"))

        if not phone:
            raise Exception("Lead phone is missing or invalid")

        vapi_assistant_id = assistant.get("vapi_assistant_id")

        if not vapi_assistant_id:
            raise Exception("Vapi assistant ID missing")

        # IMPORTANT: unified metadata
        metadata = {
            "lead_id": str(lead["id"]),
            "lead_phone": phone,
            "assistant_name": assistant["name"]
        }

        payload = {
            "assistantId": vapi_assistant_id,
            "phoneNumberId": settings.VAPI_PHONE_NUMBER_ID,
            "customer": {
                "number": phone
            },

            # KEEP ONLY THIS (most reliable)
            "metadata": metadata
        }

        logger.info(f"Vapi Payload: {payload}")

        try:
            async with httpx.AsyncClient(timeout=30) as client:

                response = await client.post(
                    f"{self.BASE_URL}/call/phone",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {settings.VAPI_API_KEY}",
                        "Content-Type": "application/json"
                    }
                )

            logger.info(f"Vapi Status: {response.status_code}")
            logger.info(f"Vapi Response: {response.text}")

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Vapi Call Failed: {str(e)}")

            try:
                error_text = response.text
            except:
                error_text = str(e)

            raise Exception(f"Vapi Response: {error_text}")

    async def create_assistant(self, data):

        payload = {
            "name": data.name,
            "firstMessage": data.first_message,
            "model": {
                "provider": data.model_provider,
                "model": data.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": data.system_prompt
                    }
                ]
            },
            "voice": {
                "provider": "vapi",
                "voiceId": data.voice_id
            }
        }

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.post(
                f"{self.BASE_URL}/assistant",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.VAPI_API_KEY}",
                    "Content-Type": "application/json"
                }
            )

        logger.info(f"Assistant Create Status: {response.status_code}")
        logger.info(f"Assistant Create Response: {response.text}")

        response.raise_for_status()
        return response.json()