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
    # HUBSPOT
    # =========================
    HUBSPOT_ACCESS_TOKEN: str

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
    # EMAIL NOTIFICATIONS
    # =========================
    ENABLE_EMAIL_NOTIFICATIONS: bool = False

    # SMTP (Gmail, Outlook, custom)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Addresses
    NOTIFICATION_EMAIL_FROM: str = ""
    NOTIFICATION_EMAIL_TO: str = ""   # comma-separated for multiple recipients

    # Dashboard URL included in email body
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