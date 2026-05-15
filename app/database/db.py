from tortoise import Tortoise
from app.core.config import settings


TORTOISE_ORM = {
    "connections": {
        "default": settings.DATABASE_URL
    },

    "apps": {
        "models": {

            "models": [
                "app.models.lead",
                "app.models.assistant",
                "app.models.call_log",
                "app.models.retry_queue",
                "aerich.models"
            ],

            "default_connection": "default"
        }
    }
}


async def init_db():

    await Tortoise.init(
        config=TORTOISE_ORM
    )

    await Tortoise.generate_schemas()


async def close_db():

    await Tortoise.close_connections()