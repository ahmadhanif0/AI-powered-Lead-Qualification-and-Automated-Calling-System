from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "call_logs" DROP COLUMN "recording_url";
        ALTER TABLE "retry_queue" ADD CONSTRAINT "fk_retry_qu_leads_3e516e96" FOREIGN KEY ("lead_id") REFERENCES "leads" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "retry_queue" DROP CONSTRAINT IF EXISTS "fk_retry_qu_leads_3e516e96";
        ALTER TABLE "call_logs" ADD "recording_url" TEXT;"""


MODELS_STATE = (
    "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"
)
