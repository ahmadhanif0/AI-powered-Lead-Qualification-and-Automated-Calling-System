from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "call_logs" ADD "recording_url" VARCHAR(500);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "call_logs" DROP COLUMN "recording_url";"""


MODELS_STATE = (
    "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"
    "0/qifm5T+jG/E7"
)
