-- =============================================================
-- Migration: Phase 2 — Advanced Features
-- Run AFTER add_auth_system.sql
-- Safe to run multiple times (IF NOT EXISTS / ON CONFLICT).
-- =============================================================

-- ── 1. retry_configs ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS retry_configs (
    id                   SERIAL PRIMARY KEY,
    user_id              INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    outcome_type         VARCHAR(50)  NOT NULL,   -- 'call_later' | 'no_response'
    retry_delay_minutes  INTEGER      NOT NULL DEFAULT 30,
    max_retry_attempts   INTEGER      NOT NULL DEFAULT 3,
    is_active            BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, outcome_type)
);

-- Default configs for every existing user
INSERT INTO retry_configs (user_id, outcome_type, retry_delay_minutes, max_retry_attempts)
SELECT id, 'call_later',  60, 3 FROM users
ON CONFLICT (user_id, outcome_type) DO NOTHING;

INSERT INTO retry_configs (user_id, outcome_type, retry_delay_minutes, max_retry_attempts)
SELECT id, 'no_response', 30, 3 FROM users
ON CONFLICT (user_id, outcome_type) DO NOTHING;

-- ── 2. scheduled_calls ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scheduled_calls (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lead_id          INTEGER      NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    assistant_id     INTEGER      NOT NULL REFERENCES assistants(id) ON DELETE CASCADE,
    scheduled_at     TIMESTAMPTZ  NOT NULL,
    celery_task_id   VARCHAR(255),
    status           VARCHAR(20)  NOT NULL DEFAULT 'pending',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_calls_user_id    ON scheduled_calls(user_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_calls_status     ON scheduled_calls(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_calls_scheduled  ON scheduled_calls(scheduled_at);

-- ── 3. Notification preferences on users ────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_on_interested      BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_on_call_completed  BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_on_retry_failed    BOOLEAN NOT NULL DEFAULT TRUE;

-- ── 4. recording_url on call_logs ────────────────────────────────────
ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS recording_url VARCHAR(500);

-- ── 5. Indexes for lead filtering ────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_leads_status      ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_lead_stage  ON leads(lead_stage);
CREATE INDEX IF NOT EXISTS idx_leads_score       ON leads(score);
CREATE INDEX IF NOT EXISTS idx_leads_ai_decision ON leads(ai_decision);

-- ── 6. Verify ────────────────────────────────────────────────────────
SELECT 'retry_configs'   AS tbl, COUNT(*) FROM retry_configs
UNION ALL
SELECT 'scheduled_calls' AS tbl, COUNT(*) FROM scheduled_calls;
