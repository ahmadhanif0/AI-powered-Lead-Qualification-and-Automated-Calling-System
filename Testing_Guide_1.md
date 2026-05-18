# Testing Guide — AI Lead Qualification System

Complete step-by-step instructions for verifying every part of the system.

---

## Prerequisites

```bash
# Start all required services before running any tests
uvicorn app.main:app --reload --port 8000          # FastAPI backend
celery -A app.queues.celery_app worker --beat --loglevel=info  # Celery worker + scheduler
redis-server                                        # Redis (if not running as a service)
cd front-end && npm run dev                         # React dashboard (port 5173)
```

---

## Section 1 — Environment Setup Testing

### 1.1 Verify .env is loaded

```bash
# Start the server and look for startup logs — no ValidationError means .env loaded
uvicorn app.main:app --reload
```

If you see `pydantic_settings.env_settings.EnvSettingsError` or `ValidationError`, a required variable is missing from `.env`.

```bash
# Quick check — print all settings (safe, no secret values printed)
python -c "from app.core.config import settings; print(settings.APP_NAME, settings.SMTP_HOST)"
```

### 1.2 Test database connection

```bash
curl http://localhost:8000/dashboard/stats
```

Expected response:
```json
{"total_leads": 0, "hot_leads": 0, "cold_leads": 0, "active_calls": 0}
```

If you get a `500` error, check `DATABASE_URL` in `.env` and that Supabase is reachable.

SQL verification:
```sql
SELECT COUNT(*) FROM leads;
SELECT COUNT(*) FROM assistants;
SELECT COUNT(*) FROM call_logs;
SELECT COUNT(*) FROM retry_queue;
```

### 1.3 Test Redis connection

```bash
redis-cli ping
# Expected: PONG

redis-cli -u redis://localhost:6379 ping
```

### 1.4 Verify HubSpot API connection

```bash
curl http://localhost:8000/hubspot/contacts
```

Expected: `{"total": N, "contacts": [...]}` where N is your HubSpot contact count.

If you get `401`, your `HUBSPOT_ACCESS_TOKEN` is invalid or expired.

### 1.5 Verify VAPI API connection

```bash
curl -H "Authorization: Bearer YOUR_VAPI_API_KEY" \
     https://api.vapi.ai/assistant
```

Expected: `200` with a list of assistants. If `401`, check `VAPI_API_KEY`.

---

## Section 2 — CRM Integration Testing

### 2.1 Manually trigger HubSpot sync

```bash
# Synchronous (waits for completion, returns result)
curl -X POST http://localhost:8000/hubspot/sync

# Asynchronous (fires Celery task, returns task_id)
curl -X POST http://localhost:8000/hubspot/sync-async
```

Expected synchronous response:
```json
{"total_contacts": 25, "created": 20, "updated": 5, "errors": 0}
```

### 2.2 Verify leads are stored

```sql
SELECT id, hubspot_id, first_name, last_name, email, phone, company,
       lead_stage, score, status
FROM leads
ORDER BY created_at DESC
LIMIT 10;
```

### 2.3 Check for duplicates

```sql
-- Should return 0 rows if duplicate prevention works
SELECT hubspot_id, COUNT(*) AS cnt
FROM leads
GROUP BY hubspot_id
HAVING COUNT(*) > 1;
```

### 2.4 Test pagination (large contact list)

Add a breakpoint or log in `hubspot_service.py` `fetch_contacts()` to confirm the `while True` loop runs multiple iterations when you have > 100 HubSpot contacts.

```bash
# Check logs for multiple page fetches
grep "Fetching page" app/logs/system.log
```

### 2.5 Verify rate-limit handling

The `HubSpotClient._request()` method handles HTTP 429 automatically. To test manually, temporarily lower the HubSpot API rate limit or mock a 429 response. Check logs for:

```
WARNING | HubSpot rate limit hit (attempt 1/3). Sleeping 10s before retry.
```

### 2.6 Expected database entries after sync

```sql
SELECT status, COUNT(*) FROM leads GROUP BY status;
-- All new leads should show status = 'Pending'

SELECT score, COUNT(*) FROM leads GROUP BY score ORDER BY score DESC;
-- Scores should range 0–100
```

---

## Section 3 — Lead Scoring Testing

### 3.1 Manual scoring test

```python
# Run from project root: python test_scoring.py
from app.services.lead_scoring_service import LeadScoringService
from datetime import datetime, timezone, timedelta

svc = LeadScoringService()

# High-value lead
print(svc.calculate_score({
    "company":    "Acme Corp Ltd",
    "email":      "ceo@acmecorp.com",
    "phone":      "+1234567890",
    "lead_stage": "opportunity",
    "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
}))
# Expected: ~100 (capped)

# Low-value lead
print(svc.calculate_score({
    "company":    None,
    "email":      "user@gmail.com",
    "phone":      None,
    "lead_stage": "subscriber",
}))
# Expected: ~25
```

### 3.2 Scoring factor breakdown

| Factor | Condition | Points |
|---|---|---|
| Base | Always | +10 |
| Company present | Any value | +20 |
| Company keywords (Inc/LLC/Corp/Ltd) | In name | +10 |
| Company name > 20 chars | No keywords | +5 |
| Business email | Not @gmail.com | +15 |
| Personal email | @gmail.com | +5 |
| Phone present | Any value | +10 |
| Stage: lead/subscriber | | +10 |
| Stage: MQL | | +25 |
| Stage: SQL | | +40 |
| Stage: opportunity | | +60 |
| Freshness: < 24h | | +15 |
| Freshness: < 7 days | | +10 |
| Freshness: < 30 days | | +5 |
| Previous "Interested" decision | ai_decision field | +20 |
| Recent call (< 7 days) | last_call_at | +5 |
| Each retry attempt | retry_count | -5 each |
| Business hours (9am–5pm UTC) | Current time | +5 |

### 3.3 Verify score in database

```sql
SELECT id, first_name, company, lead_stage, score
FROM leads
ORDER BY score DESC
LIMIT 20;
```

---

## Section 4 — AI Calling System Testing

### 4.1 Trigger a test call manually

```bash
# Replace 1 with an actual lead ID from your database
curl -X POST http://localhost:8000/calls/start/1
```

Expected response:
```json
{"message": "Call started successfully", "result": {"status": "calling", "call_id": "vapi-call-id"}}
```

Check the lead updated:
```sql
SELECT id, call_status, call_sid, last_call_at FROM leads WHERE id = 1;
-- call_status should be 'calling'
```

### 4.2 Test the decision engine with sample transcripts

```python
# python test_decision.py
from app.ai.decision_engine import DecisionEngine

engine = DecisionEngine()

tests = [
    ("I'm interested in growing my business", "Interested"),
    ("not interested, don't call me again",   "Not Interested"),
    ("I'm busy, call me later",               "Call Later"),
    ("wrong number, I don't know this person","Wrong Number"),
    ("hello? hello?",                         "No Response"),
    # Critical: "not interested" must NOT return "Interested"
    ("I am not interested at all",            "Not Interested"),
]

for transcript, expected in tests:
    result = engine.analyze(transcript)
    status = "✅" if result == expected else "❌"
    print(f"{status} '{transcript[:40]}' → {result} (expected {expected})")
```

### 4.3 Verify VAPI webhook receives callbacks

Check your ngrok dashboard at `http://localhost:4040` for incoming POST requests to `/vapi/webhook`.

Or check logs:
```bash
grep "VAPI MESSAGE TYPE" app/logs/system.log | tail -20
```

### 4.4 Check call logs in database

```sql
SELECT id, lead_id, vapi_call_id, call_status, duration_seconds,
       ai_decision, created_at
FROM call_logs
ORDER BY created_at DESC
LIMIT 10;
```

### 4.5 Verify transcripts are saved

```sql
SELECT id, last_transcript, ai_decision
FROM leads
WHERE last_transcript IS NOT NULL
ORDER BY updated_at DESC
LIMIT 5;
```

### 4.6 Simulate each VAPI webhook outcome

```bash
# Simulate "end-of-call-report" with Interested transcript
curl -X POST http://localhost:8000/vapi/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "end-of-call-report",
      "durationSeconds": 120,
      "call": {
        "id": "test-call-001",
        "metadata": {"lead_id": "1"}
      },
      "artifact": {
        "transcript": "Agent: Hi, are you interested in growing your business? Customer: Yes I am interested, tell me more."
      }
    }
  }'
```

```bash
# Simulate "customer-did-not-answer"
curl -X POST http://localhost:8000/vapi/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "status-update",
      "endedReason": "customer-did-not-answer",
      "call": {
        "id": "test-call-002",
        "metadata": {"lead_id": "1"}
      }
    }
  }'
```

---

## Section 5 — Workflow Actions Testing

### 5.1 Verify each workflow triggers correctly

After sending a webhook (Section 4.6), check:

```sql
-- After "Interested" webhook
SELECT id, status, call_status, ai_decision FROM leads WHERE id = 1;
-- status should be 'Booked', call_status 'completed'

-- After "No Response" webhook
SELECT id, status, call_status, retry_count, next_retry_at FROM leads WHERE id = 1;
-- status should be "Won't Follow Up", retry_count incremented
```

### 5.2 Check CRM updates in HubSpot

After an "Interested" decision, log into HubSpot and verify:
- Contact lifecycle stage changed to `marketingqualifiedlead`

After "Not Interested":
- Stage changed to `subscriber`

### 5.3 Verify retry queue entries

```sql
SELECT id, lead_id, retry_reason, retry_status, retry_at
FROM retry_queue
ORDER BY created_at DESC
LIMIT 10;
```

### 5.4 Test email notifications

Set `ENABLE_EMAIL_NOTIFICATIONS=true` in `.env` and configure SMTP, then trigger an "Interested" webhook (Section 4.6). Check your inbox within 30 seconds.

Check logs for:
```
INFO | Email notification sent for lead 1 (decision: Interested)
```

If email fails:
```
ERROR | Email send attempt 1 failed for lead 1: ...
ERROR | All email attempts failed for lead 1. Workflow continues.
```

### 5.5 Verify WebSocket broadcasts

Open the dashboard at `http://localhost:5173` and trigger a webhook. The "Live AI Events" panel should update in real time without a page refresh.

Or use the test script:
```bash
python test_ws.py
# Should print: LIVE EVENT: {'event': 'ai_decision', 'lead_id': 1, ...}
```

---

## Section 6 — Retry Queue Testing

### 6.1 Manually create a retry entry

```bash
# Trigger a "No Response" outcome which creates a retry
curl -X POST http://localhost:8000/vapi/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "status-update",
      "endedReason": "customer-did-not-answer",
      "call": {"id": "test-003", "metadata": {"lead_id": "2"}}
    }
  }'
```

```sql
-- Verify entry created
SELECT * FROM retry_queue WHERE lead_id = 2 ORDER BY created_at DESC LIMIT 1;
```

### 6.2 Verify Celery Beat polls correctly

Check Celery worker logs for:
```
INFO | POLL RETRY QUEUE: checking for overdue retries
INFO | POLL RETRY QUEUE: found 0 overdue retries
```

This should appear every 60 seconds.

### 6.3 Test countdown timers

To test without waiting 30 minutes, manually update `retry_at` to the past:

```sql
-- Force a retry to be overdue immediately
UPDATE retry_queue
SET retry_at = NOW() - INTERVAL '1 minute'
WHERE id = 1 AND retry_status = 'pending';
```

Within 60 seconds, the poller should pick it up. Check logs:
```
INFO | POLL RETRY QUEUE: found 1 overdue retries
INFO | POLL RETRY QUEUE: dispatched call for lead X (retry 1, reason: no_response)
```

### 6.4 Check retry_count increments

```sql
SELECT id, retry_count, next_retry_at, status FROM leads WHERE id = 2;
-- retry_count should increment by 1 each time handle_no_response fires
```

### 6.5 Verify failed retries

If a call fails (e.g. VAPI unreachable), check:
```sql
SELECT retry_status FROM retry_queue WHERE lead_id = 2;
-- Should show 'failed' after all Celery retries exhausted
```

---

## Section 7 — Dashboard Testing

### 7.1 Verify all data displays correctly

Open `http://localhost:5173`. The leads table should show:
- Name, Company, Email, Score, Stage, **Status** (Booked/Rejected/Won't Follow Up/Pending), Call Status, AI Decision, Retries

### 7.2 Test WebSocket real-time updates

1. Open dashboard in browser
2. In another terminal, send a webhook (Section 4.6)
3. The "Live AI Events" panel should update within 1 second
4. The leads table should auto-refresh (triggered by the WebSocket message)

### 7.3 Verify lead scores show

```bash
curl http://localhost:8000/dashboard/summary | python -m json.tool | grep score
```

All leads should have a numeric `score` value.

### 7.4 Test retry queue display

```bash
curl http://localhost:8000/retries/
```

The dashboard "Retry Queue" panel should show:
- Lead ID, retry reason, retry status badge
- Countdown timer ("in 28m 14s" or "5m ago (overdue)")

### 7.5 Check call status badges

After triggering a call, the dashboard should show colour-coded badges:
- 🟡 `Calling…` (yellow) — while call is in progress
- 🟢 `Completed` (green) — after end-of-call-report
- 🟠 `Not Answered` (orange) — customer-did-not-answer
- 🔴 `Rejected` (red) — customer-ended-call

---

## Section 8 — End-to-End Flow Testing

### Complete flow: HubSpot sync → AI call → decision → CRM update

**Step 1: Sync leads**
```bash
curl -X POST http://localhost:8000/hubspot/sync
```
```sql
SELECT id, first_name, score, status FROM leads ORDER BY score DESC LIMIT 5;
```

**Step 2: Verify high-score leads auto-triggered calls**
```sql
SELECT id, call_status, call_sid FROM leads WHERE score >= 50;
-- call_status should be 'calling' for high-score new leads
```

**Step 3: Simulate call completion**
```bash
curl -X POST http://localhost:8000/vapi/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "end-of-call-report",
      "durationSeconds": 95,
      "call": {
        "id": "REPLACE_WITH_REAL_VAPI_CALL_ID",
        "metadata": {"lead_id": "REPLACE_WITH_LEAD_ID"}
      },
      "artifact": {
        "transcript": "Agent: Hi, are you interested? Customer: Yes I am interested, tell me more about the price."
      }
    }
  }'
```

**Step 4: Verify all updates**
```sql
-- Lead updated
SELECT id, status, call_status, ai_decision, score FROM leads WHERE id = LEAD_ID;
-- status = 'Booked', call_status = 'completed', ai_decision = 'Interested'

-- Call log updated
SELECT vapi_call_id, transcript, ai_decision, duration_seconds, call_status
FROM call_logs WHERE lead_id = LEAD_ID;

-- No retry created for Interested leads
SELECT COUNT(*) FROM retry_queue WHERE lead_id = LEAD_ID;
-- Should be 0
```

**Step 5: Verify HubSpot updated**
Log into HubSpot → Contacts → find the contact → check lifecycle stage = `marketingqualifiedlead`.

**Step 6: Verify email sent** (if enabled)
Check inbox for subject: `🔥 New Interested Lead: {name}`

**Expected timeline:**
| Event | Time |
|---|---|
| Sync triggered | T+0s |
| Leads created in DB | T+2–10s |
| High-score calls fired | T+10–30s |
| VAPI places call | T+30–60s |
| Call completes | T+60–180s |
| Webhook received | T+180s |
| DB updated | T+181s |
| Email sent | T+182s |
| Dashboard updates | T+182s (WebSocket) |

---

## Section 9 — Error Handling Testing

### 9.1 Test API failures

```bash
# Disconnect from internet, then trigger a sync
curl -X POST http://localhost:8000/hubspot/sync
# Should return 500 with error detail, not crash the server
```

Check logs:
```bash
grep "ERROR" app/logs/system.log | tail -20
```

### 9.2 Verify Celery auto-retry

Stop the VAPI service (or use an invalid API key temporarily), then trigger a retry call. Check Celery logs for:
```
ERROR | RETRY TASK FAILED FOR LEAD 1: ...
WARNING | Task retry_call_task[...] retry: Retry in 300s
```

After 3 failures:
```
ERROR | Task retry_call_task[...] raised unexpected: ...
```

### 9.3 Test rate-limit handling

Check `hubspot_client.py` logs when HubSpot returns 429:
```
WARNING | HubSpot rate limit hit (attempt 1/3). Sleeping 10s before retry.
```

### 9.4 Check error logs

```bash
# View all errors in the log file
grep "ERROR" app/logs/system.log

# View last 50 log lines
tail -50 app/logs/system.log

# Watch logs in real time
Get-Content app/logs/system.log -Wait   # PowerShell
```

---

## Section 10 — Performance Testing

### 10.1 Test with 100+ leads

```bash
# Sync all HubSpot contacts (no limit)
curl -X POST http://localhost:8000/hubspot/sync
```

Monitor:
```sql
-- Check sync progress
SELECT COUNT(*), status FROM leads GROUP BY status;

-- Check for errors
SELECT COUNT(*) FROM leads WHERE score = 0;  -- leads that may have failed scoring
```

### 10.2 Verify queue processing speed

```bash
# Monitor Celery task throughput
celery -A app.queues.celery_app inspect active
celery -A app.queues.celery_app inspect reserved
celery -A app.queues.celery_app inspect stats
```

### 10.3 Monitor Celery worker load

```bash
# Real-time Celery monitoring (install flower first: pip install flower)
celery -A app.queues.celery_app flower --port=5555
# Open http://localhost:5555
```

Flower shows:
- Active tasks
- Task history and success/failure rates
- Worker CPU and memory usage
- Queue depths

---

## Troubleshooting Common Issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| `ValidationError` on startup | Missing `.env` variable | Copy `.env.example` to `.env` and fill all values |
| `500` on `/dashboard/stats` | DB not connected | Check `DATABASE_URL`, run `aerich upgrade` |
| HubSpot sync returns 0 contacts | Invalid token | Regenerate `HUBSPOT_ACCESS_TOKEN` in HubSpot |
| VAPI call not placed | Missing `VAPI_PHONE_NUMBER_ID` | Set in `.env` from VAPI dashboard |
| Webhook not received | ngrok not running | Start ngrok, update `TWILIO_WEBHOOK_URL` |
| Retry queue not processing | Celery Beat not running | Add `--beat` flag to celery worker command |
| Email not sending | SMTP credentials wrong | Use Gmail App Password, not account password |
| `Not Interested` detected as `Interested` | Old decision_engine.py | Ensure negative keywords are checked first |
| `duration_seconds` is 0 | VAPI payload structure | Confirmed fixed — reads from `message` level |
| Dashboard shows stale data | WebSocket disconnected | Check WS status indicator, refresh page |

---

## Quick Reference — Useful SQL Queries

```sql
-- Full lead overview
SELECT id, first_name, last_name, company, score, status,
       call_status, ai_decision, retry_count
FROM leads ORDER BY score DESC;

-- Leads by status
SELECT status, COUNT(*) FROM leads GROUP BY status;

-- Recent call logs
SELECT cl.id, cl.lead_id, cl.call_status, cl.ai_decision,
       cl.duration_seconds, cl.created_at
FROM call_logs cl ORDER BY cl.created_at DESC LIMIT 20;

-- Pending retries with lead info
SELECT rq.id, rq.lead_id, l.first_name, l.company,
       rq.retry_reason, rq.retry_status, rq.retry_at
FROM retry_queue rq
JOIN leads l ON l.id = rq.lead_id
WHERE rq.retry_status IN ('pending', 'processing')
ORDER BY rq.retry_at;

-- Overdue retries (should be 0 if poller is running)
SELECT COUNT(*) AS overdue
FROM retry_queue
WHERE retry_status = 'pending'
  AND retry_at < NOW();

-- Leads with transcripts
SELECT id, first_name, ai_decision,
       LEFT(last_transcript, 100) AS transcript_preview
FROM leads
WHERE last_transcript IS NOT NULL
ORDER BY updated_at DESC;
```

---

## Quick Reference — curl Commands

```bash
# Health check
curl http://localhost:8000/

# Dashboard stats
curl http://localhost:8000/dashboard/stats

# All leads
curl http://localhost:8000/dashboard/summary

# HubSpot contacts (raw)
curl http://localhost:8000/hubspot/contacts

# Sync HubSpot
curl -X POST http://localhost:8000/hubspot/sync

# Start a call
curl -X POST http://localhost:8000/calls/start/1

# List assistants
curl http://localhost:8000/assistants/

# Retry queue
curl http://localhost:8000/retries/

# Create assistant
curl -X POST http://localhost:8000/assistants/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales Assistant",
    "system_prompt": "You are a sales qualification agent...",
    "first_message": "Hi, I am calling about your business growth.",
    "voice_id": "Elliot",
    "model_provider": "openai",
    "model_name": "gpt-4.1"
  }'
```
