-- =============================================================
-- Migration: Replace API-key CRM storage with OAuth tokens
-- Run ONCE in Supabase SQL editor.
-- =============================================================

-- ── 1. Add OAuth columns ─────────────────────────────────────────────
ALTER TABLE user_crms
    ADD COLUMN IF NOT EXISTS access_token      TEXT,
    ADD COLUMN IF NOT EXISTS refresh_token     TEXT,
    ADD COLUMN IF NOT EXISTS token_expires_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS hubspot_portal_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS updated_at        TIMESTAMPTZ DEFAULT NOW();

-- ── 2. Drop old API-key columns (no longer used) ─────────────────────
ALTER TABLE user_crms
    DROP COLUMN IF EXISTS api_key,
    DROP COLUMN IF EXISTS api_secret;

-- ── 3. Add unique constraint (user + crm_type) if not already present ─
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uid_user_crms_user_id_crm_type'
    ) THEN
        ALTER TABLE user_crms
            ADD CONSTRAINT uid_user_crms_user_id_crm_type
            UNIQUE (user_id, crm_type);
    END IF;
END $$;

-- ── 4. Remove old HubSpot connections (force OAuth reconnect) ─────────
-- Users will need to reconnect via Settings → HubSpot Integration.
DELETE FROM user_crms WHERE crm_type = 'hubspot';

-- ── 5. Verify ─────────────────────────────────────────────────────────
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'user_crms'
ORDER BY ordinal_position;
