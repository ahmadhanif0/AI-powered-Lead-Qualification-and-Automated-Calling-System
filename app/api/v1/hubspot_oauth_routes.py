"""
HubSpot OAuth 2.0 flow.

Endpoints:
  GET  /crm/hubspot/connect          → returns authorization_url to redirect user
  GET  /crm/hubspot/callback         → exchanges code for tokens, stores in DB
  POST /crm/hubspot/refresh-token    → manually refresh an expired token
  GET  /crm/hubspot/status           → check connection status for current user
  DELETE /crm/hubspot/disconnect     → remove tokens and mark disconnected
"""

from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.user_crm import UserCRM
from app.core.config import settings
from app.services.activity_logger import log_activity
from app.logs.logger import logger

router = APIRouter(prefix="/crm/hubspot", tags=["HubSpot OAuth"])

HUBSPOT_AUTH_URL  = "https://app.hubspot.com/oauth/authorize"
HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
HUBSPOT_SCOPES    = "crm.objects.contacts.read crm.objects.contacts.write crm.schemas.contacts.read"


# ── GET /crm/hubspot/connect ─────────────────────────────────────────

@router.get("/connect")
async def initiate_hubspot_oauth(current_user: User = Depends(get_current_user)):
    """Return the HubSpot authorization URL. Frontend redirects the user there."""
    params = {
        "client_id":    settings.HUBSPOT_CLIENT_ID,
        "redirect_uri": settings.HUBSPOT_REDIRECT_URI,
        "scope":        HUBSPOT_SCOPES,
        "state":        f"user_{current_user.id}",
    }
    auth_url = f"{HUBSPOT_AUTH_URL}?{urlencode(params)}"

    await log_activity(current_user.id, "initiate_hubspot_oauth")

    return {"authorization_url": auth_url}


# ── GET /crm/hubspot/callback ────────────────────────────────────────

@router.get("/callback")
async def hubspot_oauth_callback(
    code:  str = Query(..., description="Authorization code from HubSpot"),
    state: str = Query(..., description="State parameter containing user_<id>"),
):
    """
    HubSpot redirects here after the user authorizes.
    Exchanges the code for tokens and stores them in user_crms.
    Then redirects the browser back to the frontend dashboard.
    """
    # Validate state
    if not state.startswith("user_"):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    try:
        user_id = int(state.replace("user_", ""))
    except ValueError:
        raise HTTPException(status_code=400, detail="Malformed state parameter")

    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Exchange code for tokens
    token_data = {
        "grant_type":    "authorization_code",
        "client_id":     settings.HUBSPOT_CLIENT_ID,
        "client_secret": settings.HUBSPOT_CLIENT_SECRET,
        "redirect_uri":  settings.HUBSPOT_REDIRECT_URI,
        "code":          code,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post(
                HUBSPOT_TOKEN_URL,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        access_token  = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")
        expires_in    = tokens.get("expires_in", 3600)
        expires_at    = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Fetch HubSpot portal ID
        async with httpx.AsyncClient(timeout=10) as client:
            acct_resp = await client.get(
                "https://api.hubapi.com/account-info/v3/details",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        portal_id = None
        if acct_resp.status_code == 200:
            portal_id = str(acct_resp.json().get("portalId", ""))

        # Upsert UserCRM record
        user_crm = await UserCRM.get_or_none(user_id=user_id, crm_type="hubspot")
        if user_crm:
            user_crm.access_token      = access_token
            user_crm.refresh_token     = refresh_token
            user_crm.token_expires_at  = expires_at
            user_crm.hubspot_portal_id = portal_id
            user_crm.is_connected      = True
            await user_crm.save()
        else:
            await UserCRM.create(
                user_id=user_id,
                crm_type="hubspot",
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=expires_at,
                hubspot_portal_id=portal_id,
                is_connected=True,
            )

        await log_activity(user_id, "hubspot_oauth_success", {"portal_id": portal_id})
        logger.info(f"HubSpot OAuth success for user {user_id}, portal {portal_id}")

    except httpx.HTTPStatusError as e:
        logger.error(f"HubSpot token exchange failed: {e.response.text}")
        return RedirectResponse(url=f"{settings.DASHBOARD_URL}/settings?hubspot=error")
    except Exception as e:
        logger.error(f"HubSpot OAuth unexpected error: {e}")
        return RedirectResponse(url=f"{settings.DASHBOARD_URL}/settings?hubspot=error")

    # Redirect browser back to frontend settings page with success flag
    return RedirectResponse(url=f"{settings.DASHBOARD_URL}/settings?hubspot=connected")


# ── POST /crm/hubspot/refresh-token ─────────────────────────────────

@router.post("/refresh-token")
async def refresh_hubspot_token(current_user: User = Depends(get_current_user)):
    """Manually refresh an expired HubSpot access token."""
    user_crm = await UserCRM.get_or_none(user_id=current_user.id, crm_type="hubspot")
    if not user_crm or not user_crm.refresh_token:
        raise HTTPException(status_code=404, detail="HubSpot not connected or no refresh token")

    from app.crm.hubspot_client import HubSpotClient
    try:
        await HubSpotClient._refresh_token(user_crm)
        return {"message": "Token refreshed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── GET /crm/hubspot/status ──────────────────────────────────────────

@router.get("/status")
async def get_hubspot_status(current_user: User = Depends(get_current_user)):
    """Return the HubSpot connection status for the current user."""
    user_crm = await UserCRM.get_or_none(user_id=current_user.id, crm_type="hubspot")

    if not user_crm:
        return {"is_connected": False, "portal_id": None, "last_sync_at": None, "is_expired": False}

    is_expired = False
    if user_crm.token_expires_at:
        is_expired = datetime.now(timezone.utc) >= user_crm.token_expires_at

    return {
        "is_connected":     user_crm.is_connected and not is_expired,
        "portal_id":        user_crm.hubspot_portal_id,
        "last_sync_at":     user_crm.last_sync_at.isoformat() if user_crm.last_sync_at else None,
        "token_expires_at": user_crm.token_expires_at.isoformat() if user_crm.token_expires_at else None,
        "is_expired":       is_expired,
    }


# ── DELETE /crm/hubspot/disconnect ───────────────────────────────────

@router.delete("/disconnect")
async def disconnect_hubspot(current_user: User = Depends(get_current_user)):
    """Remove HubSpot tokens and mark as disconnected."""
    user_crm = await UserCRM.get_or_none(user_id=current_user.id, crm_type="hubspot")
    if not user_crm:
        raise HTTPException(status_code=404, detail="HubSpot not connected")

    portal_id = user_crm.hubspot_portal_id
    await user_crm.delete()

    await log_activity(current_user.id, "hubspot_disconnected", {"portal_id": portal_id})
    return {"message": "HubSpot disconnected successfully"}
