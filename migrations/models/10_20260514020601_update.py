from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "leads" ADD "assistant_id" INT;
        ALTER TABLE "leads" ADD CONSTRAINT "fk_leads_assistan_d42696e0" FOREIGN KEY ("assistant_id") REFERENCES "assistants" ("id") ON DELETE SET NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "leads" DROP CONSTRAINT IF EXISTS "fk_leads_assistan_d42696e0";
        ALTER TABLE "leads" DROP COLUMN "assistant_id";"""


MODELS_STATE = (
    "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"
    "WF7+A/+cNUs="
)
