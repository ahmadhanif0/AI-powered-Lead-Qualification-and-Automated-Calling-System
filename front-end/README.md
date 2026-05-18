Let me read every file in the project before writing a single line of the map.

Read file(s)

main.py

config.py

db.py

lead.py

assistant.py

call_log.py

retry_queue.py

lead_repository.py

call_log_repository.py

retry_queue_repository.py

hubspot_routes.py

call_routes.py

assistant_routes.py

dashboard_routes.py

retry_routes.py

vapi_webhook.py

twilio_webhook.py

routes.py

manager.py

celery_app.py

tasks.py

lead_sync_service.py

lead_scoring_service.py

assistant_service.py

assistant_router.py

crm_update_service.py

notification_service.py

ai_conversation_scoring_service.py

call_service.py

decision_engine.py

vapi_client.py

hubspot_client.py

hubspot_service.py

workflow_engine.py

actions.py

logger.py

App.jsx
Now I have every file. Here is the complete map.

Complete Project Flow & File Connection Map
1. Project Entry Point
Main file: 
main.py

Startup sequence:

uvicorn app.main:app loads the module
Settings() in config.py runs immediately at import time — reads .env via pydantic-settings
logger in 
logger.py
 is instantiated at import time
FastAPI lifespan() runs on first request: logs key prefixes, calls init_db() → Tortoise ORM connects to PostgreSQL and generates schemas
On shutdown: close_db() closes all DB connections
Routers registered in main.py:

Router variable	Source file	URL prefix
hubspot_router	
hubspot_routes.py
/hubspot
vapi_router	
vapi_webhook.py
(no prefix)
assistant_router	
assistant_routes.py
/assistants
call_router	
call_routes.py
/calls
dashboard_router	
dashboard_routes.py
/dashboard
ws_router	
routes.py
(no prefix)
twilio_router	
twilio_webhook.py
(no prefix)
retry_router	
retry_routes.py
/retries
2. Complete Request Flows
Scenario A — HubSpot Sync
POST /hubspot/sync
  │
  └─► hubspot_routes.py :: sync_hubspot_contacts()
        │
        └─► LeadSyncService :: sync_hubspot_leads()
              │
              ├─► HubSpotService :: fetch_contacts()
              │     │
              │     └─► HubSpotClient :: get_contacts(after=cursor)
              │           │  loops with pagination until paging=None
              │           └─► GET https://api.hubapi.com/crm/v3/objects/contacts
              │                 (Bearer HUBSPOT_ACCESS_TOKEN)
              │                 retries on 429/5xx via _request()
              │
              └─► for each contact:
                    │
                    ├─► LeadScoringService :: calculate_score(lead_data)
                    │     returns float 0–100
                    │
                    ├─► LeadRepository :: get_by_hubspot_id()
                    │     READ  leads WHERE hubspot_id = ?
                    │
                    ├─► if exists:
                    │     LeadRepository :: update_lead()
                    │       WRITE leads SET name/email/phone/company/stage/score
                    │
                    └─► if new:
                          LeadRepository :: create_lead()
                            WRITE INSERT INTO leads
                          │
                          └─► if score >= 50:
                                start_lead_call_task.delay(lead_id)
                                  → Redis queue → Celery worker
POST /hubspot/sync-async does the same but fires sync_hubspot_leads_task.delay() to Celery instead of running inline.

Scenario B — AI Call Triggered
POST /calls/start/{lead_id}
  │
  └─► call_routes.py :: start_call(lead_id)
        │
        └─► CallService :: start_call(lead_id, is_retry=False)
              │
              ├─► LeadRepository :: get_by_id(lead_id)
              │     READ leads WHERE id = ?
              │
              ├─► [guard] if last_call_at < 20s ago → raise Exception
              │
              ├─► AssistantRouter :: select_assistant(lead_data)
              │     │  score>=70 or stage=opportunity/sql → "sales" assistant
              │     │  score>=40 → "growth" assistant
              │     │  else → "support" assistant
              │     └─► AssistantService :: list_assistants()
              │           READ SELECT * FROM assistants
              │
              ├─► LeadRepository :: assign_assistant(lead_id, assistant_id)
              │     WRITE leads SET assistant_id = ?
              │
              ├─► VapiClient :: make_call(lead, assistant)
              │     │  formats phone (+92 prefix)
              │     └─► POST https://api.vapi.ai/call/phone
              │           { assistantId, phoneNumberId, customer.number, metadata:{lead_id} }
              │           Bearer VAPI_API_KEY
              │           returns { id: vapi_call_id }
              │
              ├─► LeadRepository :: update_call_status(status="calling", call_sid=vapi_call_id)
              │     WRITE leads SET call_status, last_call_at, call_sid, call_provider
              │
              ├─► CallLogRepository :: create_log(...)
              │     WRITE INSERT INTO call_logs
              │
              └─► ConnectionManager :: broadcast({event:"call_started"})
                    → all connected WebSocket clients (App.jsx)

─────────────────────────────────────────────────────────────
  [VAPI places the call via Twilio, call happens, call ends]
─────────────────────────────────────────────────────────────

POST /vapi/webhook  ← VAPI calls this when call ends
  │
  ├─► [if type="status-update" AND endedReason="customer-did-not-answer"]
  │     LeadRepository :: update_call_status("call_not_attended")
  │     CallLogRepository :: update_log(call_status)
  │     WorkflowEngine :: handle_result(lead, "No Response")
  │       → actions.handle_no_response()  [see Scenario D]
  │
  ├─► [if type="status-update" AND endedReason="customer-ended-call"]
  │     LeadRepository :: update_call_status("call_rejected")
  │     CallLogRepository :: update_log(call_status)
  │
  └─► [if type="end-of-call-report"]
        │
        ├─► extract transcript from artifact.transcript or artifact.messages
        ├─► extract duration from message.durationSeconds or call.durationSeconds
        ├─► extract lead_id from call.metadata.lead_id
        │
        ├─► DecisionEngine :: analyze(transcript)
        │     keyword matching → "Interested"/"Not Interested"/"Call Later"/
        │                         "Wrong Number"/"No Response"
        │
        ├─► AIConversationScoringService :: calculate_score(transcript, decision)
        │     returns delta score -100 to +100
        │
        ├─► LeadRepository :: update_lead_score(lead_id, ai_score)
        │     WRITE leads SET score += ai_score  (clamped 0–100)
        │
        ├─► LeadRepository :: save_transcript_and_decision(lead_id, transcript, decision)
        │     WRITE leads SET last_transcript, ai_decision
        │
        ├─► LeadRepository :: update_call_status(lead_id, "completed")
        │     WRITE leads SET call_status, last_call_at
        │
        ├─► CallLogRepository :: update_log(vapi_call_id, {transcript, ai_decision,
        │     call_status, duration_seconds})
        │     WRITE call_logs SET ...
        │
        └─► WorkflowEngine :: handle_result(lead, result)
              → [see Scenario D]
Scenario C — Retry Call (Celery Beat)
Celery Beat scheduler (every 60 seconds)
  │
  └─► poll_retry_queue_task()   [tasks.py]
        │
        ├─► init_db()  ← Tortoise needs its own connection in worker process
        │
        ├─► RetryQueue.filter(retry_status="pending", retry_at__lte=now)
        │     READ SELECT * FROM retry_queue WHERE ...
        │
        └─► for each overdue entry:
              │
              ├─► entry.retry_status = "processing"
              │     WRITE retry_queue SET retry_status
              │
              └─► retry_call_task.delay(lead.id)
                    → Redis queue

retry_call_task(lead_id)   [tasks.py]
  │
  ├─► init_db()
  │
  ├─► CallService :: start_call(lead_id, is_retry=True)
  │     [is_retry=True skips the 20-second duplicate guard]
  │     [same flow as Scenario B from VapiClient onwards]
  │
  ├─► on success:
  │     RetryQueueRepository :: mark_completed_for_lead(lead_id)
  │       WRITE retry_queue SET retry_status="completed"
  │
  └─► on failure:
        RetryQueueRepository :: mark_failed_for_lead(lead_id)
          WRITE retry_queue SET retry_status="failed"
        raises → Celery auto-retries up to 3× (300s, 600s, 1200s backoff)
Celery Beat also runs sync_hubspot_leads_task at the top of every hour via crontab(minute=0).

Scenario D — Workflow Action (Interested example)
WorkflowEngine :: handle_result(lead, "Interested")
  │  lowercases result → "interested"
  │
  └─► WorkflowActions :: handle_interested(lead)
        │
        ├─► LeadRepository :: update_lead_status(lead_id, "Booked")
        │     WRITE leads SET status = "Booked"
        │
        ├─► LeadRepository :: update_call_status(lead_id, "completed")
        │     WRITE leads SET call_status, last_call_at
        │
        ├─► CRMUpdateService :: update_stage(lead_id, "marketingqualifiedlead")
        │     READ  leads WHERE id = lead_id  (to get hubspot_id)
        │     PATCH https://api.hubapi.com/crm/v3/objects/contacts/{hubspot_id}
        │       { properties: { lifecyclestage: "marketingqualifiedlead" } }
        │     WRITE leads SET lead_stage = "marketingqualifiedlead"
        │
        ├─► CRMUpdateService :: update_lead_status_in_crm(lead_id, "Booked")
        │     maps "Booked" → "opportunity" via STATUS_TO_HUBSPOT_STAGE dict
        │     PATCH https://api.hubapi.com/crm/v3/objects/contacts/{hubspot_id}
        │       { properties: { lifecyclestage: "opportunity" } }
        │     WRITE leads SET lead_stage = "opportunity"
        │
        ├─► ConnectionManager :: broadcast({event:"ai_decision", decision:"Interested", status:"Booked"})
        │     → all WebSocket clients → App.jsx updates live events panel
        │     → App.jsx also calls loadLeads() + loadRetries() on this event
        │
        └─► NotificationService :: send_notification(lead, "Interested")
              logs to console always
              if ENABLE_EMAIL_NOTIFICATIONS=true:
                runs _send_email() in thread executor
                  smtplib.SMTP → STARTTLS → login → sendmail
                  retries once on failure, then logs error and continues
For other outcomes:

Call Later → status="Pending", CRM stage="lead", creates retry_queue row, fires retry_call_task in 3600s
Not Interested → status="Rejected", CRM stage="subscriber"
Wrong Number → status="Rejected", no CRM stage update
No Response → status="Won't Follow Up", creates retry_queue row, fires retry_call_task in 1800s
3. File Responsibility Map
File	Responsibility
main.py
FastAPI app factory — registers all routers, runs DB init/close on startup/shutdown, logs env key prefixes
config.py
Reads .env via pydantic-settings into a typed Settings singleton used everywhere
logger.py
Creates a stdlib logging.Logger that writes to console + 
system.log
db.py
Tortoise ORM config dict, init_db() and close_db() functions
lead.py
ORM definition for the leads table — 20 fields
assistant.py
ORM definition for the assistants table — 8 fields
call_log.py
ORM definition for the call_logs table — 9 fields
retry_queue.py
ORM definition for the retry_queue table — 5 fields
lead_repository.py
All DB read/write operations for the leads table — 10 methods
call_log_repository.py
create_log() and update_log() for call_logs table
retry_queue_repository.py
CRUD for retry_queue — create, get pending, mark completed/failed
hubspot_routes.py
HTTP routes: GET /hubspot/contacts, POST /hubspot/sync, POST /hubspot/sync-async
call_routes.py
HTTP route: POST /calls/start/{lead_id}
assistant_routes.py
HTTP routes: POST/GET /assistants/ — create and list AI assistants
dashboard_routes.py
HTTP routes: GET /dashboard/stats, /summary, /live-leads — reads directly from Lead model
retry_routes.py
HTTP route: GET /retries/ — returns pending retry queue entries
debug_routes.py
Temporary debug routes: /debug/config, /debug/vapi, /debug/hubspot
vapi_webhook.py
POST /vapi/webhook — receives VAPI call events, runs decision engine, updates DB, triggers workflow
twilio_webhook.py
POST /twilio/voice — returns TwiML; WS /ws/twilio-media/{lead_id} — Twilio media stream bridge
routes.py
WS /ws — accepts frontend WebSocket connections, delegates to ConnectionManager
manager.py
ConnectionManager singleton — holds active WebSocket list, broadcast() sends JSON to all
twilio_vapi_bridge.py
TwilioVapiBridge — handles Twilio audio stream (partially implemented)
celery_app.py
Creates Celery app with Redis broker/backend, defines beat_schedule (poll every 60s, sync every hour)
tasks.py
4 Celery tasks: sync_hubspot_leads_task, start_lead_call_task, retry_call_task, poll_retry_queue_task
lead_sync_service.py
Orchestrates full HubSpot→DB sync with per-contact error isolation
lead_scoring_service.py
Calculates lead score 0–100 from 9 factors (company, email, phone, stage, freshness, engagement, timezone)
ai_conversation_scoring_service.py
Calculates post-call score delta from transcript keywords and decision
assistant_service.py
Creates assistants in VAPI then saves locally; lists/gets from DB
assistant_router.py
Selects which assistant to use based on lead score and stage
crm_update_service.py
Pushes lifecycle stage and status updates to HubSpot via HubSpotClient
notification_service.py
Logs sales alerts; sends SMTP email (HTML+plain) when ENABLE_EMAIL_NOTIFICATIONS=true
call_service.py
Orchestrates a full outbound call: fetch lead → select assistant → call VAPI → update DB → broadcast WS
decision_engine.py
Pure keyword matching on transcript → returns one of 5 decision strings
vapi_client.py
HTTP client for VAPI API: make_call() and create_assistant(); uses Twilio SDK to fetch phone number
hubspot_client.py
HTTP client for HubSpot API with rate-limit (429) and 5xx retry logic
hubspot_service.py
Wraps HubSpotClient.get_contacts() in a pagination loop
workflow_engine.py
Routes a decision string to the correct WorkflowActions handler
actions.py
5 handlers (Interested/CallLater/NotInterested/WrongNumber/NoResponse) — each updates DB, CRM, WebSocket, and optionally email/retry
assistant_schema.py
Pydantic request body schema for POST /assistants/
App.jsx
React dashboard — fetches leads + retries on load, connects WebSocket for live events, renders table with status badges
4. File Connection Map
main.py
  ├── imports config.py          (settings singleton)
  ├── imports logger.py          (logger singleton)
  ├── imports database/db.py     (init_db, close_db)
  ├── imports hubspot_routes.py  → imports HubSpotService, LeadSyncService, tasks.py
  ├── imports vapi_webhook.py    → imports DecisionEngine, WorkflowEngine, LeadRepository,
  │                                         CallLogRepository, AIConversationScoringService
  ├── imports assistant_routes.py → imports AssistantService, assistant_schema.py
  ├── imports call_routes.py     → imports CallService
  ├── imports dashboard_routes.py → imports Lead (model directly)
  ├── imports websocket/routes.py → imports ConnectionManager
  ├── imports twilio_webhook.py  → imports ConnectionManager, TwilioVapiBridge,
  │                                         LeadRepository, config
  └── imports retry_routes.py   → imports RetryQueueRepository

CallService (ai/call_service.py)
  ├── imports VapiClient
  ├── imports LeadRepository
  ├── imports CallLogRepository
  ├── imports AssistantService
  ├── imports AssistantRouter    → imports AssistantService
  └── imports ConnectionManager

VapiClient (ai/vapi_client.py)
  ├── imports config.py          (VAPI_API_KEY, VAPI_PHONE_NUMBER_ID,
  │                               TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
  ├── imports logger.py
  └── uses twilio.rest.Client    (to fetch phone number)

WorkflowEngine (workflows/workflow_engine.py)
  └── imports WorkflowActions

WorkflowActions (workflows/actions.py)
  ├── imports LeadRepository
  ├── imports RetryQueueRepository
  ├── imports CRMUpdateService   → imports HubSpotClient
  ├── imports NotificationService → imports config.py
  ├── imports ConnectionManager
  └── imports retry_call_task, start_lead_call_task (from tasks.py)

tasks.py (queues/tasks.py)
  ├── imports celery_app.py      → imports config.py (REDIS_URL)
  ├── imports LeadSyncService    → imports HubSpotService, LeadRepository,
  │                                         LeadScoringService
  ├── imports CallService
  └── imports database/db.py    (init_db — each task creates its own DB connection)

LeadSyncService (services/lead_sync_service.py)
  ├── imports H
A network error occurred. Please check your connection and try again.

.............................................................................

How Login Works
Both users and admins use the same login page at http://localhost:5173/login. There is no separate admin login — the system checks the role field in the database after login and shows different UI accordingly.

Flow:

Enter email + password → POST /auth/login → JWT token returned
→ token stored in localStorage → redirected to dashboard
→ sidebar shows "Admin" section only if role = "admin"
Default Admin Credentials
The admin account was created by 
add_auth_system.sql
:

Field	Value
Email	admin@example.com
Password	Admin@1234
Role	admin
How a New Admin is Created
There are two ways, both require an existing admin:

Way 1 — Admin panel in the UI
Login as admin → go to Admin → Users
Click New User
Fill in email, password, full name
Set Role = Admin
Click Create
Way 2 — API call
# First get an admin token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin@1234"}'

# Use that token to create a new admin
curl -X POST http://localhost:8000/admin/users \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"newadmin@example.com","password":"NewAdmin@1234","full_name":"New Admin","role":"admin"}'
Way 3 — Direct SQL (if you're locked out)
Run this in Supabase SQL editor:

-- First generate a hash by running in your terminal:
-- python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('YourPassword@123'))"

INSERT INTO users (email, password_hash, full_name, role, is_active)
VALUES (
    'newadmin@company.com',
    '$2b$12$PASTE_YOUR_GENERATED_HASH_HERE',
    'New Admin',
    'admin',
    TRUE
)
ON CONFLICT (email) DO NOTHING;
How Regular Users Sign Up
Regular users go to http://localhost:5173/signup and fill in name, email, password. They always get role = "user" — they cannot self-assign admin. Only an existing admin can promote someone to admin via the admin panel or API.

What Each Role Can See
Feature	User	Admin
Dashboard	Own leads only	All leads
Assistants	Own assistants	All assistants
HubSpot sync	Own leads	Own leads
Settings	Own retry config, CRM, notifications	Same
Admin → Users	❌ Hidden	✅ Full CRUD
Admin → Analytics	❌ Hidden	✅ Global stats
