from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.hubspot_routes import router as hubspot_router
from app.webhooks.vapi_webhook import router as vapi_router
from app.api.v1.assistant_routes import router as assistant_router
from app.api.v1.call_routes import router as call_router
from app.api.v1.dashboard_routes import router as dashboard_router
from app.websocket.routes import router as ws_router
from app.webhooks.twilio_webhook import router as twilio_router
from app.api.v1.retry_routes import router as retry_router

from app.database.db import init_db, close_db
from app.core.config import settings
from app.logs.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):

    # ── Startup diagnostics ──────────────────────────────────────────
    # Print first 12 chars of each key so you can confirm the right
    # value is loaded without exposing the full secret in logs.
    logger.info("=" * 55)
    logger.info("STARTUP — environment variable check")
    logger.info(f"  VAPI_API_KEY        : {settings.VAPI_API_KEY[:12]}...")
    logger.info(f"  VAPI_ASSISTANT_ID   : {(settings.VAPI_ASSISTANT_ID or 'NOT SET')[:12]}...")
    logger.info(f"  VAPI_PHONE_NUMBER_ID: {(settings.VAPI_PHONE_NUMBER_ID or 'NOT SET')[:12]}...")
    logger.info(f"  HUBSPOT_TOKEN       : {settings.HUBSPOT_ACCESS_TOKEN[:12]}...")
    logger.info(f"  TWILIO_SID          : {settings.TWILIO_ACCOUNT_SID[:12]}...")
    logger.info("=" * 55)
    # ────────────────────────────────────────────────────────────────

    await init_db()

    yield

    await close_db()


app = FastAPI(title="AI Lead System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hubspot_router)
app.include_router(vapi_router)
app.include_router(assistant_router)
app.include_router(call_router)
app.include_router(dashboard_router)
app.include_router(ws_router)
app.include_router(twilio_router)
app.include_router(retry_router)