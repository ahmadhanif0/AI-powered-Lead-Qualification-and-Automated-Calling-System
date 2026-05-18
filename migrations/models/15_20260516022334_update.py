from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "password_hash" VARCHAR(255) NOT NULL,
    "full_name" VARCHAR(255) NOT NULL,
    "role" VARCHAR(20) NOT NULL DEFAULT 'user',
    "is_active" BOOL NOT NULL DEFAULT True,
    "is_suspended" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_login" TIMESTAMPTZ
);
        CREATE TABLE IF NOT EXISTS "user_crms" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "crm_type" VARCHAR(50) NOT NULL,
    "api_key" VARCHAR(500) NOT NULL,
    "api_secret" VARCHAR(500),
    "is_connected" BOOL NOT NULL DEFAULT False,
    "last_sync_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "user_activities" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "action" VARCHAR(100) NOT NULL,
    "details" JSONB,
    "ip_address" VARCHAR(50),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "assistants" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "system_prompt" TEXT NOT NULL,
    "first_message" TEXT NOT NULL,
    "voice_id" VARCHAR(100) NOT NULL DEFAULT 'Elliot',
    "model_provider" VARCHAR(50) NOT NULL DEFAULT 'openai',
    "model_name" VARCHAR(50) NOT NULL DEFAULT 'gpt-4.1',
    "vapi_assistant_id" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT REFERENCES "users" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "leads" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "hubspot_id" VARCHAR(255) NOT NULL UNIQUE,
    "first_name" VARCHAR(255),
    "last_name" VARCHAR(255),
    "email" VARCHAR(255),
    "phone" VARCHAR(100),
    "company" VARCHAR(255),
    "lead_stage" VARCHAR(255),
    "score" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "status" VARCHAR(100) NOT NULL DEFAULT 'Pending',
    "call_status" VARCHAR(50) NOT NULL DEFAULT 'pending',
    "call_sid" VARCHAR(255),
    "call_provider" VARCHAR(100),
    "last_call_at" TIMESTAMPTZ,
    "retry_count" INT NOT NULL DEFAULT 0,
    "last_transcript" TEXT,
    "ai_decision" VARCHAR(100),
    "next_retry_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "assistant_id" INT REFERENCES "assistants" ("id") ON DELETE SET NULL,
    "user_id" INT REFERENCES "users" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "call_logs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "lead_id" INT NOT NULL,
    "vapi_call_id" VARCHAR(255),
    "twilio_number" VARCHAR(100),
    "assistant_name" VARCHAR(255),
    "transcript" TEXT,
    "ai_decision" VARCHAR(100),
    "call_status" VARCHAR(100) NOT NULL DEFAULT 'queued',
    "duration_seconds" INT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT REFERENCES "users" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "retry_queue" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "retry_reason" VARCHAR(100) NOT NULL,
    "retry_status" VARCHAR(100) NOT NULL DEFAULT 'pending',
    "retry_at" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "lead_id" INT NOT NULL REFERENCES "leads" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "leads";
        DROP TABLE IF EXISTS "users";
        DROP TABLE IF EXISTS "call_logs";
        DROP TABLE IF EXISTS "retry_queue";
        DROP TABLE IF EXISTS "user_crms";
        DROP TABLE IF EXISTS "user_activities";
        DROP TABLE IF EXISTS "assistants";"""


MODELS_STATE = (
    "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"
)
