from tortoise import Tortoise
from app.core.config import settings


TORTOISE_ORM = {
    "connections": {"default": settings.DATABASE_URL},
    "apps": {
        "models": {
            "models": [
                "app.models.user",
                "app.models.user_crm",
                "app.models.user_activity",
                "app.models.retry_config",
                "app.models.lead",
                "app.models.assistant",
                "app.models.call_log",
                "app.models.retry_queue",
                "app.models.scheduled_call",
                "aerich.models",
            ],
            "default_connection": "default",
        }
    },
}


async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()


async def close_db():
    await Tortoise.close_connections()
