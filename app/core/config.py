from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # =========================
    # DATABASE
    # =========================
    DATABASE_URL: str

    # =========================
    # REDIS / CELERY
    # =========================
    REDIS_URL: str

    # =========================
    # HUBSPOT OAuth
    # =========================
    # Legacy token kept optional so existing .env files don't break
    # immediately. Remove once all users have migrated to OAuth.
    HUBSPOT_ACCESS_TOKEN: str = ""

    HUBSPOT_CLIENT_ID:     str = ""
    HUBSPOT_CLIENT_SECRET: str = ""
    HUBSPOT_REDIRECT_URI:  str = "http://localhost:8000/crm/hubspot/callback"

    # =========================
    # VAPI
    # =========================
    VAPI_API_KEY: str
    VAPI_ASSISTANT_ID: str | None = None
    VAPI_PHONE_NUMBER_ID: str | None = None

    # =========================
    # TWILIO
    # =========================
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WEBHOOK_URL: str

    # =========================
    # JWT / AUTH
    # =========================
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # =========================
    # EMAIL NOTIFICATIONS
    # =========================
    ENABLE_EMAIL_NOTIFICATIONS: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFICATION_EMAIL_FROM: str = ""
    NOTIFICATION_EMAIL_TO: str = ""
    DASHBOARD_URL: str = "http://localhost:5173"

    # =========================
    # APP
    # =========================
    APP_NAME: str = "AI Lead Qualification System"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
