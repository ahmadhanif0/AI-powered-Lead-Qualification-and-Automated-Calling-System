import asyncio
import httpx

from app.core.config import settings
from app.logs.logger import logger


class HubSpotClient:
    BASE_URL   = "https://api.hubapi.com"
    MAX_RETRIES = 3

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.HUBSPOT_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal helper: execute a request with rate-limit / retry logic.
    # Handles HTTP 429 (Too Many Requests) by reading the Retry-After
    # header and sleeping before retrying.  Other 5xx errors use
    # exponential backoff (2s, 4s, 8s).
    # ------------------------------------------------------------------
    async def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:

        for attempt in range(1, self.MAX_RETRIES + 1):
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method, url, headers=self.headers, **kwargs
                )

            # ---- Rate limited ----
            if response.status_code == 429:
                retry_after = int(
                    response.headers.get("Retry-After", 10)
                )
                logger.warning(
                    f"HubSpot rate limit hit (attempt {attempt}/"
                    f"{self.MAX_RETRIES}). "
                    f"Sleeping {retry_after}s before retry."
                )
                await asyncio.sleep(retry_after)
                continue

            # ---- Server error — exponential backoff ----
            if response.status_code >= 500 and attempt < self.MAX_RETRIES:
                wait = 2 ** attempt  # 2s, 4s, 8s
                logger.warning(
                    f"HubSpot server error {response.status_code} "
                    f"(attempt {attempt}/{self.MAX_RETRIES}). "
                    f"Retrying in {wait}s."
                )
                await asyncio.sleep(wait)
                continue

            # ---- Success or non-retryable error ----
            response.raise_for_status()
            return response

        # All retries exhausted
        response.raise_for_status()
        return response

    # ------------------------------------------------------------------
    async def get_contacts(self, after: str = None, limit: int = 100):
        url = f"{self.BASE_URL}/crm/v3/objects/contacts"

        params = {
            "limit": limit,
            "properties": [
                "firstname",
                "lastname",
                "email",
                "phone",
                "company",
                "lifecyclestage",
            ],
        }

        if after:
            params["after"] = after

        response = await self._request("GET", url, params=params)
        return response.json()

    # ------------------------------------------------------------------
    async def update_contact_stage(self, contact_id: str, stage: str):
        url = f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}"

        payload = {
            "properties": {
                "lifecyclestage": stage
            }
        }

        response = await self._request("PATCH", url, json=payload)
        return response.json()
