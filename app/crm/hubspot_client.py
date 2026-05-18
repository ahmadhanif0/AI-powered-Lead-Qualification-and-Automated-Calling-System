import asyncio
from datetime import datetime, timezone, timedelta

import httpx

from app.core.config import settings
from app.logs.logger import logger

HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"


class HubSpotClient:
    BASE_URL    = "https://api.hubapi.com"
    MAX_RETRIES = 3

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        }

    # ── Factory: build a client for a specific user, auto-refreshing if needed ──

    @classmethod
    async def for_user(cls, user) -> "HubSpotClient":
        """
        Create a HubSpotClient using the OAuth token stored for `user`.
        Automatically refreshes the token if it has expired.
        Raises ValueError if HubSpot is not connected for this user.
        """
        from app.models.user_crm import UserCRM

        user_crm = await UserCRM.get_or_none(user_id=user.id, crm_type="hubspot")

        if not user_crm:
            logger.info(f"[HubSpot] No UserCRM record found for user_id={user.id}")
            raise ValueError("HubSpot not connected for this user")

        if not user_crm.is_connected or not user_crm.access_token:
            logger.info(
                f"[HubSpot] UserCRM found for user_id={user.id} but "
                f"is_connected={user_crm.is_connected} access_token={'set' if user_crm.access_token else 'MISSING'}"
            )
            raise ValueError("HubSpot not connected for this user")

        logger.info(
            f"[HubSpot] UserCRM found for user_id={user.id} "
            f"portal_id={user_crm.hubspot_portal_id} "
            f"expires_at={user_crm.token_expires_at}"
        )

        # Auto-refresh if token is expired (or within 60 s of expiry)
        if user_crm.token_expires_at:
            expires_soon = user_crm.token_expires_at - timedelta(seconds=60)
            now = datetime.now(timezone.utc)
            if now >= expires_soon:
                logger.info(
                    f"[HubSpot] Token expired/expiring for user_id={user.id} "
                    f"(expires_at={user_crm.token_expires_at}, now={now}) — refreshing"
                )
                await cls._refresh_token(user_crm)
            else:
                logger.info(f"[HubSpot] Token valid for user_id={user.id}")

        return cls(user_crm.access_token)

    @staticmethod
    async def _refresh_token(user_crm) -> None:
        """Exchange refresh_token for a new access_token and persist it."""
        if not user_crm.refresh_token:
            user_crm.is_connected = False
            await user_crm.save()
            raise ValueError("No refresh token available — user must reconnect HubSpot")

        data = {
            "grant_type":    "refresh_token",
            "client_id":     settings.HUBSPOT_CLIENT_ID,
            "client_secret": settings.HUBSPOT_CLIENT_SECRET,
            "refresh_token": user_crm.refresh_token,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    HUBSPOT_TOKEN_URL,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            response.raise_for_status()
            tokens = response.json()

            user_crm.access_token     = tokens["access_token"]
            user_crm.refresh_token    = tokens.get("refresh_token", user_crm.refresh_token)
            expires_in                = tokens.get("expires_in", 3600)
            user_crm.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            await user_crm.save()

            logger.info(f"HubSpot token refreshed for user_crm {user_crm.id}")

        except Exception as e:
            user_crm.is_connected = False
            await user_crm.save()
            raise ValueError(f"Failed to refresh HubSpot token: {e}")

    # ── Internal request helper with rate-limit / retry logic ──────────

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        for attempt in range(1, self.MAX_RETRIES + 1):
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(method, url, headers=self.headers, **kwargs)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                logger.warning(f"HubSpot rate limit (attempt {attempt}/{self.MAX_RETRIES}). Sleeping {retry_after}s.")
                await asyncio.sleep(retry_after)
                continue

            if response.status_code >= 500 and attempt < self.MAX_RETRIES:
                wait = 2 ** attempt
                logger.warning(f"HubSpot server error {response.status_code} (attempt {attempt}). Retrying in {wait}s.")
                await asyncio.sleep(wait)
                continue

            response.raise_for_status()
            return response

        response.raise_for_status()
        return response

    # ── Public API methods ──────────────────────────────────────────────

    async def get_contacts(self, after: str = None, limit: int = 100):
        url    = f"{self.BASE_URL}/crm/v3/objects/contacts"
        params = {
            "limit":      limit,
            "properties": ["firstname", "lastname", "email", "phone", "company", "lifecyclestage"],
        }
        if after:
            params["after"] = after

        response = await self._request("GET", url, params=params)
        return response.json()

    async def update_contact_stage(self, contact_id: str, stage: str):
        """Update only the lifecycle stage of a HubSpot contact."""
        safe_stage = self._safe_hs_stage(stage)
        if not safe_stage:
            logger.warning(f"[HubSpot] update_contact_stage: invalid stage '{stage}' — skipping")
            return {}
        url     = f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}"
        payload = {"properties": {"lifecyclestage": safe_stage}}
        response = await self._request("PATCH", url, json=payload)
        return response.json()

    async def update_contact(self, contact_id: str, data: dict) -> dict:
        """
        Update any fields on a HubSpot contact.
        Accepted keys: firstname, lastname, email, phone, company, lifecyclestage
        Only non-empty values are sent. lifecyclestage is validated before sending.
        """
        properties: dict = {}
        for key in ("firstname", "lastname", "email", "phone", "company"):
            val = data.get(key)
            if val is not None and str(val).strip() != "":
                properties[key] = str(val).strip()

        raw_stage = data.get("lifecyclestage")
        if raw_stage:
            safe_stage = self._safe_hs_stage(raw_stage)
            if safe_stage:
                properties["lifecyclestage"] = safe_stage

        url     = f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}"
        payload = {"properties": properties}
        logger.info(f"[HubSpot] update_contact id={contact_id} payload: {payload}")
        response = await self._request("PATCH", url, json=payload)
        return response.json()

    # Valid HubSpot lifecyclestage values (anything else causes a 400)
    _VALID_HS_STAGES = {
        "subscriber", "lead", "marketingqualifiedlead", "salesqualifiedlead",
        "opportunity", "customer", "evangelist", "other",
    }

    # Map our internal stage names → nearest valid HubSpot lifecyclestage
    _STAGE_TO_HS = {
        "new":            "lead",
        "contacted":      "lead",
        "qualified":      "marketingqualifiedlead",
        "interested":     "salesqualifiedlead",
        "not_interested": "lead",
        "call_later":     "lead",
        "wrong_number":   "lead",
        "booked":         "customer",
    }

    @classmethod
    def _safe_hs_stage(cls, stage: str | None) -> str | None:
        """
        Convert an internal stage value to a valid HubSpot lifecyclestage.
        Returns None if the value cannot be mapped (so it's omitted from the payload).
        """
        if not stage:
            return None
        lower = stage.lower()
        if lower in cls._VALID_HS_STAGES:
            return lower
        mapped = cls._STAGE_TO_HS.get(lower)
        if mapped:
            return mapped
        logger.warning(f"[HubSpot] Unknown stage '{stage}' — omitting lifecyclestage from payload")
        return None

    async def create_contact(self, data: dict) -> dict:
        """
        Create a new contact in HubSpot.

        Accepted keys (all optional except email):
            firstname, lastname, email, phone, company, lifecyclestage

        Field name rules (HubSpot API):
            - "firstname"  NOT "first_name"
            - "lastname"   NOT "last_name"
            - lifecyclestage must be a valid HubSpot enum value

        Returns the created contact dict (includes 'id').
        If the contact already exists (409), fetches and returns the existing contact instead.
        """
        # ── Build safe properties dict ───────────────────────────────
        # 1. Only the five standard writable fields + lifecyclestage
        # 2. Strip None / empty strings
        # 3. Map lifecyclestage to a valid HubSpot enum (or omit it)
        raw_stage = data.get("lifecyclestage")
        safe_stage = self._safe_hs_stage(raw_stage)

        properties: dict = {}
        for key in ("firstname", "lastname", "email", "phone", "company"):
            val = data.get(key)
            if val is not None and str(val).strip() != "":
                properties[key] = str(val).strip()

        if safe_stage:
            properties["lifecyclestage"] = safe_stage

        url     = f"{self.BASE_URL}/crm/v3/objects/contacts"
        payload = {"properties": properties}

        logger.info(f"[HubSpot] create_contact payload: {payload}")

        try:
            response = await self._request("POST", url, json=payload)
            result = response.json()
            logger.info(f"[HubSpot] create_contact SUCCESS id={result.get('id')} email={data.get('email')}")
            return result

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code

            if status_code == 409:
                # Contact already exists — find and return the existing one
                email = data.get("email", "")
                logger.warning(
                    f"[HubSpot] create_contact 409 — contact already exists for email={email}. "
                    "Fetching existing contact."
                )
                try:
                    existing = await self._get_contact_by_email(email)
                    if existing:
                        logger.info(f"[HubSpot] Found existing contact id={existing.get('id')} for email={email}")
                        return existing
                except Exception as fetch_err:
                    logger.error(f"[HubSpot] Failed to fetch existing contact for email={email}: {fetch_err}")
                # Return a minimal dict so the caller can still mark hubspot_pushed=True
                return {"id": None, "existing": True, "email": email}

            elif status_code == 401:
                logger.error(
                    f"[HubSpot] create_contact 401 Unauthorized — token may be invalid or expired. "
                    f"Response: {e.response.text[:300]}"
                )
                raise

            else:
                logger.error(
                    f"[HubSpot] create_contact HTTP {status_code} for email={data.get('email')}: "
                    f"{e.response.text[:300]}"
                )
                raise

    async def _get_contact_by_email(self, email: str) -> dict | None:
        """Look up a HubSpot contact by email address."""
        url = f"{self.BASE_URL}/crm/v3/objects/contacts/search"
        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "email",
                    "operator":     "EQ",
                    "value":        email,
                }]
            }],
            "properties": ["firstname", "lastname", "email", "phone", "company", "lifecyclestage"],
            "limit": 1,
        }
        response = await self._request("POST", url, json=payload)
        data = response.json()
        results = data.get("results", [])
        return results[0] if results else None
