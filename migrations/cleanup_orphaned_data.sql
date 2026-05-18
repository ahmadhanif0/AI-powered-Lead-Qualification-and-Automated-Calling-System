-- =============================================================
-- Cleanup: Remove orphaned data from before multi-tenant migration
-- Run ONCE in Supabase SQL editor.
-- Preview counts first, then uncomment the DELETE statements.
-- =============================================================

-- ── 1. Preview what will be deleted ──────────────────────────────────
SELECT 'orphaned leads'      AS type, COUNT(*) FROM leads      WHERE user_id IS NULL
UNION ALL
SELECT 'orphaned assistants' AS type, COUNT(*) FROM assistants WHERE user_id IS NULL
UNION ALL
SELECT 'orphaned call_logs'  AS type, COUNT(*) FROM call_logs  WHERE user_id IS NULL
UNION ALL
SELECT 'orphaned retry_queue' AS type, COUNT(*)
FROM retry_queue
WHERE lead_id NOT IN (SELECT id FROM leads);

-- ── 2. Delete orphaned data ───────────────────────────────────────────
-- Uncomment after reviewing the preview above.

-- Delete retry_queue entries whose lead no longer exists
DELETE FROM retry_queue
WHERE lead_id NOT IN (SELECT id FROM leads);

-- Delete call_logs without a user
DELETE FROM call_logs WHERE user_id IS NULL;

-- Delete leads without a user
DELETE FROM leads WHERE user_id IS NULL;

-- Delete assistants without a user
DELETE FROM assistants WHERE user_id IS NULL;

-- ── 3. Verify ─────────────────────────────────────────────────────────
SELECT 'remaining orphaned leads'      AS check, COUNT(*) FROM leads      WHERE user_id IS NULL
UNION ALL
SELECT 'remaining orphaned assistants' AS check, COUNT(*) FROM assistants WHERE user_id IS NULL
UNION ALL
SELECT 'remaining orphaned call_logs'  AS check, COUNT(*) FROM call_logs  WHERE user_id IS NULL;
-- All counts should be 0
