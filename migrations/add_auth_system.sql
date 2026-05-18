-- =============================================================
-- Migration: Add JWT auth + multi-tenancy
-- IDEMPOTENT — safe to run multiple times.
-- All statements use IF NOT EXISTS / IF EXISTS / ON CONFLICT.
-- =============================================================

-- ── 1. Create users table ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL       NOT NULL PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(255) NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'user',
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    is_suspended  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_login    TIMESTAMPTZ
);

-- ── 2. Create user_crms table ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_crms (
    id           SERIAL       NOT NULL PRIMARY KEY,
    user_id      INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    crm_type     VARCHAR(50)  NOT NULL,
    api_key      VARCHAR(500) NOT NULL,
    api_secret   VARCHAR(500),
    is_connected BOOLEAN      NOT NULL DEFAULT FALSE,
    last_sync_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── 3. Create user_activities table ─────────────────────────────────
CREATE TABLE IF NOT EXISTS user_activities (
    id         SERIAL       NOT NULL PRIMARY KEY,
    user_id    INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action     VARCHAR(100) NOT NULL,
    details    JSONB,
    ip_address VARCHAR(50),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── 4. Add user_id to existing tables (IF NOT EXISTS) ───────────────
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE assistants
    ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE call_logs
    ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;

-- ── 5. Indexes ───────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_created  ON user_activities(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_user_id            ON leads(user_id);
CREATE INDEX IF NOT EXISTS idx_assistants_user_id       ON assistants(user_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_user_id        ON call_logs(user_id);

-- ── 6. Default admin user ────────────────────────────────────────────
-- Password: Admin@1234
-- Regenerate hash: python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('Admin@1234'))"
INSERT INTO users (email, password_hash, full_name, role, is_active)
VALUES (
    'admin@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK8i',
    'Admin User',
    'admin',
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- ── 7. Migrate existing data to admin user ───────────────────────────
DO $$
DECLARE admin_id INTEGER;
BEGIN
    SELECT id INTO admin_id FROM users WHERE email = 'admin@example.com';
    IF admin_id IS NOT NULL THEN
        UPDATE leads      SET user_id = admin_id WHERE user_id IS NULL;
        UPDATE assistants SET user_id = admin_id WHERE user_id IS NULL;
        UPDATE call_logs  SET user_id = admin_id WHERE user_id IS NULL;
    END IF;
END $$;

-- ── 8. Tell Aerich this migration is already applied ─────────────────
-- This prevents Aerich from trying to run migration 13 again
-- since the columns already exist from this SQL script.
INSERT INTO aerich (version, app, content)
VALUES (
    '13_add_auth_system',
    'models',
    '{"version": "13_add_auth_system", "app": "models"}'
)
ON CONFLICT DO NOTHING;

-- ── 9. Verify ────────────────────────────────────────────────────────
SELECT 'users'                AS table_name, COUNT(*) AS rows FROM users
UNION ALL
SELECT 'leads with user_id',              COUNT(*) FROM leads      WHERE user_id IS NOT NULL
UNION ALL
SELECT 'assistants with user_id',         COUNT(*) FROM assistants WHERE user_id IS NOT NULL
UNION ALL
SELECT 'call_logs with user_id',          COUNT(*) FROM call_logs  WHERE user_id IS NOT NULL;
