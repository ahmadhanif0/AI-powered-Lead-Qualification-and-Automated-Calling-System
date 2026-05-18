from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.v1.auth_routes         import router as auth_router
from app.api.v1.admin_routes         import router as admin_router
from app.api.v1.admin_analytics      import router as admin_analytics_router
from app.api.v1.hubspot_routes       import router as hubspot_router
from app.api.v1.hubspot_oauth_routes import router as hubspot_oauth_router
from app.api.v1.assistant_routes     import router as assistant_router
from app.api.v1.call_routes          import router as call_router
from app.api.v1.dashboard_routes     import router as dashboard_router
from app.api.v1.retry_routes         import router as retry_router
from app.api.v1.retry_config_routes  import router as retry_config_router
from app.api.v1.crm_routes           import router as crm_router
from app.api.v1.leads                import router as leads_router
from app.api.v1.user_routes          import router as user_router
from app.webhooks.vapi_webhook       import router as vapi_router
from app.webhooks.twilio_webhook     import router as twilio_router
from app.websocket.routes            import router as ws_router

from app.database.db  import init_db, close_db
from app.core.config  import settings
from app.logs.logger  import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 55)
    logger.info("STARTUP — environment variable check")
    logger.info(f"  VAPI_API_KEY        : {settings.VAPI_API_KEY[:12]}...")
    logger.info(f"  VAPI_PHONE_NUMBER_ID: {(settings.VAPI_PHONE_NUMBER_ID or 'NOT SET')[:12]}...")
    logger.info(f"  HUBSPOT_CLIENT_ID   : {settings.HUBSPOT_CLIENT_ID[:12] if settings.HUBSPOT_CLIENT_ID else 'NOT SET'}...")
    logger.info(f"  TWILIO_SID          : {settings.TWILIO_ACCOUNT_SID[:12]}...")
    logger.info(f"  JWT_SECRET_KEY      : {settings.JWT_SECRET_KEY[:12]}...")
    logger.info("=" * 55)
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="AI Lead System",
    description="AI-powered lead qualification and outreach system. Use the **Authorize** button to paste your Bearer token.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public (no auth)
app.include_router(auth_router)
app.include_router(vapi_router)
app.include_router(twilio_router)
app.include_router(ws_router)
app.include_router(hubspot_oauth_router)   # callback must be public (no token yet)

# Protected
app.include_router(hubspot_router)
app.include_router(assistant_router)
app.include_router(call_router)
app.include_router(dashboard_router)
app.include_router(retry_router)
app.include_router(retry_config_router)
app.include_router(crm_router)
app.include_router(leads_router)
app.include_router(user_router)

# Admin-only
app.include_router(admin_router)
app.include_router(admin_analytics_router)


# ── Swagger: inject HTTPBearer security scheme ───────────────────────
# This makes the Swagger UI show an "Authorize" button where you can
# paste a raw JWT token (without typing "Bearer " prefix).
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add HTTPBearer security scheme
    schema.setdefault("components", {})
    schema["components"].setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Paste your access_token here (without 'Bearer ' prefix)",
    }

    # Endpoints that must remain public — no Bearer token required
    PUBLIC_PATHS = {
        "/auth/login",
        "/auth/signup",
        "/auth/refresh",
        "/vapi/webhook",
        "/twilio/voice",
        "/ws",
        "/crm/hubspot/callback",   # OAuth callback — no token exists yet at this point
    }

    # Apply HTTPBearer to every operation EXCEPT public ones
    for path, path_data in schema.get("paths", {}).items():
        for operation in path_data.values():
            if path in PUBLIC_PATHS:
                # Explicitly mark as no security so Swagger shows no padlock
                operation["security"] = []
            else:
                operation.setdefault("security", [{"HTTPBearer": []}])

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
