from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "retry_configs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "outcome_type" VARCHAR(50) NOT NULL,
    "retry_delay_minutes" INT NOT NULL DEFAULT 30,
    "max_retry_attempts" INT NOT NULL DEFAULT 3,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_retry_confi_user_id_2a96e3" UNIQUE ("user_id", "outcome_type")
);
        CREATE TABLE IF NOT EXISTS "scheduled_calls" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "scheduled_at" TIMESTAMPTZ NOT NULL,
    "celery_task_id" VARCHAR(255),
    "status" VARCHAR(20) NOT NULL DEFAULT 'pending',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "assistant_id" INT NOT NULL REFERENCES "assistants" ("id") ON DELETE CASCADE,
    "lead_id" INT NOT NULL REFERENCES "leads" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
        ALTER TABLE "users" ADD IF NOT EXISTS "email_on_interested" BOOL NOT NULL DEFAULT True;
        ALTER TABLE "users" ADD IF NOT EXISTS "email_on_call_completed" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "users" ADD IF NOT EXISTS "email_on_retry_failed" BOOL NOT NULL DEFAULT True;
        ALTER TABLE "call_logs" ADD IF NOT EXISTS "recording_url" VARCHAR(500);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" DROP COLUMN "email_on_interested";
        ALTER TABLE "users" DROP COLUMN "email_on_call_completed";
        ALTER TABLE "users" DROP COLUMN "email_on_retry_failed";
        ALTER TABLE "call_logs" DROP COLUMN "recording_url";
        DROP TABLE IF EXISTS "retry_configs";
        DROP TABLE IF EXISTS "scheduled_calls";"""


MODELS_STATE = (
    "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"
    "2OXA8vg/6Yk8gA=="
)
