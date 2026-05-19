Complete Project Documentation
Stack Overview
Layer	Technology
Backend	FastAPI (Python), Tortoise ORM, PostgreSQL (Supabase)
Task Queue	Celery + Redis
AI Calls	VAPI (voice AI) + Twilio (phone numbers)
CRM	HubSpot (OAuth 2.0)
Frontend	React + Tailwind CSS
Auth	JWT (access + refresh tokens)
1. Call Flow — End to End
How a call starts
A call can be triggered three ways:

A) Manual from UI — User clicks "Call" on a lead in Dashboard or Leads page → POST /calls/start/{lead_id} → call_routes.py → start_call() → CallService.start_call()

B) Retry — After a "Call Later" or "No Response" outcome, WorkflowActions schedules retry_call_task.apply_async(args=[lead_id], countdown=delay_seconds) in actions.py. Celery fires it after the countdown.

C) Scheduled — User schedules a call via POST /calls/schedule → creates a ScheduledCall record → dispatches scheduled_call_task.apply_async(args=[sc.id], countdown=seconds_until) in call_routes.py.

What CallService does (app/ai/call_service.py → CallService.start_call())
Fetches the lead from DB
Checks for duplicate calls — if last_call_at was less than 20 seconds ago and it's not a retry, raises an exception (prevents accidental double-clicks)
Calls AssistantRouter.select_assistant() to pick which assistant to use
Links the assistant to the lead via LeadRepository.assign_assistant()
Calls VapiClient.make_call() — sends a POST to https://api.vapi.ai/call/phone with assistantId, phoneNumberId, customer.number, and metadata: {lead_id, lead_phone, assistant_name}
VAPI returns a call object with an id (the vapi_call_id)
Updates lead call_status = "calling" and call_sid = vapi_call_id
Creates a CallLog record with call_status = "calling" and the vapi_call_id
Broadcasts a WebSocket event {event: "call_started", lead_id, status: "calling"}
Phone number formatting (vapi_client.py → _format_phone())
Strips spaces and dashes
If starts with "0" → replaces with "+92" (Pakistani number format)
If doesn't start with "+" → prepends "+92"
⚠️ This is hardcoded for Pakistan (+92). International numbers from other countries will be incorrectly formatted.
VAPI webhook events (
vapi_webhook.py
)
VAPI sends POST requests to /vapi/webhook during and after the call. Two event types are handled:

status-update — fires during the call when something changes:

If endedReason == "customer-did-not-answer" → sets call_status = "call_not_attended" on lead and call log, then triggers WorkflowEngine.handle_result(result="No Response")
If endedReason == "customer-ended-call" → sets call_status = "call_rejected" on lead and call log, returns without running workflow
All other status updates → ignored
end-of-call-report — fires when the call fully ends with a transcript:

Extracts vapi_call_id, durationSeconds (checked at message level first, then call object level)
Extracts lead_id from call.metadata.lead_id
Extracts transcript from artifact.transcript or reconstructs it from artifact.messages[]
Runs DecisionEngine.analyze(transcript) → gets AI decision string
Runs AIConversationScoringService.calculate_score() → gets a score delta
Updates lead score via LeadRepository.update_lead_score()
Saves transcript and decision via LeadRepository.save_transcript_and_decision() → sets lead.last_transcript and lead.ai_decision
Sets lead.call_status = "completed"
Updates the CallLog record with transcript, ai_decision, call_status, duration_seconds, recording_url
Runs WorkflowEngine.handle_result(result=decision) — wrapped in try/except with a fallback status map so a CRM failure never prevents the status from being saved
2. Transcript Saving
When: At the end of a call, when VAPI sends the end-of-call-report webhook.

Where saved: Two places simultaneously:

leads.last_transcript (TextField) — plain text, format: "assistant: Hello\nuser: Yes I'm interested\n..." — saved by LeadRepository.save_transcript_and_decision() in lead_repository.py
call_logs.transcript (TextField) — same plain text format — saved by CallLogRepository.update_log() in call_log_repository.py
Format: Raw string with lines like "role: message text". The LiveTranscriptModal backend endpoint (GET /calls/leads/{id}/live-transcript in call_routes.py) parses this into [{role: "assistant"|"user", text: "..."}] by splitting on ": ".

⚠️ If VAPI sends artifact.transcript as a pre-formatted string, it's used directly. If not, it's reconstructed from artifact.messages[] array. The two formats may differ slightly.

3. AI Decision / Score
Decision Engine (app/ai/decision_engine.py → DecisionEngine.analyze())
Pure keyword matching on the lowercased transcript. Priority order (first match wins):

Wrong Number — checks: "wrong number", "wrong person", "not the right number" → returns "Wrong Number"
Not Interested — checks ~25 phrases like "not interested", "don't call", "waste of time" → returns "Not Interested"
Call Later — checks: "call later", "call me back", "not a good time", "i'm busy" → returns "Call Later"
Interested — checks ~19 phrases like "i'm interested", "tell me more", "what's the price", "sign me up" → returns "Interested"
Fallback — if nothing matches → returns "No Response"
⚠️ This is entirely keyword-based — no actual AI/LLM involved in the decision. A lead saying "I'm not interested in marketing" would match "interested in marketing" (Interested) before "not interested" because the Not Interested check runs first. Actually it would correctly catch "not interested" first since that check runs before Interested. But edge cases exist.

AI Conversation Score (
ai_conversation_scoring_service.py
)
Not read yet — this is a separate score delta applied on top of the lead score after a call. It's called in the webhook but the file wasn't in the read list.

Lead Score (app/services/lead_scoring_service.py → LeadScoringService.calculate_score())
Composite 0–100 score calculated from:

Factor	Points
Base (every lead)	+10
Company present	+20
Company has formal keywords (Inc, LLC, Corp)	+10
Company name > 20 chars	+5
Business email (non-Gmail)	+15
Personal email (Gmail)	+5
Phone present	+10
Stage = lead/subscriber	+10
Stage = marketingqualifiedlead	+25
Stage = salesqualifiedlead	+40
Stage = opportunity	+60
Lead < 24 hours old	+15
Lead < 7 days old	+10
Lead < 30 days old	+5
Previous ai_decision = "interested"	+20
Called within last 7 days	+5
Each retry attempt	-5
Current UTC hour is 9am–5pm	+5
Score is clamped to [0, 100]. Calculated on: lead creation, CSV import, lead update (PUT endpoint), and after each call (via AIConversationScoringService delta).

4. Lead Status Update
Possible statuses (defined in leads.py → VALID_STATUSES)
"Pending", "Booked", "Rejected", "Won't Follow Up"

Automatic update after a call
Flow: VAPI webhook → DecisionEngine → WorkflowEngine.handle_result() → WorkflowActions:

AI Decision	Lead Status	Call Status	Action
Interested	Booked	completed	CRM updated, notification sent
Call Later	Pending	call_later	Retry scheduled
Not Interested	Won't Follow Up	completed	CRM updated
Wrong Number	Rejected	wrong_number	CRM updated
No Response	Rejected	call_not_attended	Retry scheduled
Each path calls LeadRepository.update_lead_status(lead_id, status) in lead_repository.py which does lead.status = status; await lead.save().

Fallback safety net (vapi_webhook.py): If WorkflowEngine throws any exception (e.g. CRM failure), the webhook catches it and directly calls update_lead_status() using a hardcoded decision→status map. This ensures status is always saved even if CRM sync fails.

Manual update
PUT /leads/{id} in leads.py → update_lead() — accepts optional status field in UpdateLeadRequest. Validates against VALID_STATUSES, logs the override, saves to DB. Also available via the Edit modal in the frontend.

5. Score Calculation
Covered in section 3. Score is stored in leads.score (FloatField, default 0). Updated:

On lead creation (POST /leads/create) — LeadScoringService.calculate_score()
On CSV import — same service
On lead update (PUT /leads/{id}) — recalculated from updated contact info
After a call — AIConversationScoringService adds a delta to the existing score (clamped to 0–100)
6. Workflow Engine
WorkflowEngine (
workflow_engine.py
) — thin router. Takes the AI decision string, lowercases it, and dispatches to the correct WorkflowActions method.

WorkflowActions (
actions.py
) — does the actual work for each outcome:

handle_interested() — sets status=Booked, call_status=completed, syncs to HubSpot, broadcasts WebSocket, sends notification
handle_call_later() — fetches user's retry delay from RetryConfig (or falls back to 3600s/60min), sets status=Pending, increments retry_count, sets next_retry_at, creates RetryQueue entry, fires retry_call_task.apply_async(countdown=delay_seconds)
handle_not_interested() — sets status="Won't Follow Up", call_status=completed, syncs to HubSpot, broadcasts WebSocket
handle_wrong_number() — sets status=Rejected, call_status=wrong_number, syncs to HubSpot, broadcasts WebSocket
handle_no_response() — fetches user's retry delay for "no_response" (or falls back to 1800s/30min), sets status=Rejected, increments retry_count, creates RetryQueue entry, fires retry_call_task.apply_async(countdown=delay_seconds)
_get_retry_delay(user_id, outcome_type) — looks up RetryConfig for the user and outcome type. If found and is_active=True, returns retry_delay_minutes * 60. Otherwise returns the hardcoded default.

7. HubSpot Integration
Connection method
OAuth 2.0. No API key. Each user connects their own HubSpot account.

OAuth flow (
hubspot_oauth_routes.py
)
GET /crm/hubspot/connect — returns an authorization URL pointing to https://app.hubspot.com/oauth/authorize with scopes: crm.objects.contacts.read, crm.objects.contacts.write, crm.schemas.contacts.read. State parameter encodes user_{id}.
User is redirected to HubSpot, approves access
HubSpot redirects to GET /crm/hubspot/callback?code=...&state=user_123
Backend exchanges the code for tokens via POST to https://api.hubapi.com/oauth/v1/token
Fetches portal ID from https://api.hubapi.com/account-info/v3/details
Upserts a UserCRM record with access_token, refresh_token, token_expires_at, hubspot_portal_id, is_connected=True
Redirects browser to {DASHBOARD_URL}/settings?hubspot=connected
Token storage (
user_crm.py
)
Table: user_crms. Columns: access_token (TextField), refresh_token (TextField), token_expires_at (DatetimeField), hubspot_portal_id, is_connected.

Token expiry and refresh (app/crm/hubspot_client.py → HubSpotClient.for_user())
HubSpot access tokens expire in ~6 hours (3600s default, actual value from expires_in in token response). The system auto-refreshes:

Every time HubSpotClient.for_user(user) is called, it checks if token_expires_at - 60 seconds <= now
If yes, calls _refresh_token(user_crm) which POSTs to https://api.hubapi.com/oauth/v1/token with grant_type=refresh_token
New access_token, refresh_token, and token_expires_at are saved to DB
If refresh fails (e.g. refresh token revoked), sets is_connected=False and raises ValueError
What data is synced to HubSpot
Operation	When	Fields
Create contact	Manual lead create, CSV import	firstname, lastname, email, phone, company, lifecyclestage
Update contact stage	After call outcome (WorkflowActions)	lifecyclestage only
Update contact info	Lead edit (PUT /leads/{id})	firstname, lastname, email, phone, company
Delete/archive contact	Lead delete	Archives via DELETE /crm/v3/objects/contacts/{id}
Stage mapping (hubspot_client.py → _STAGE_TO_HS, crm_update_service.py → STATUS_TO_HUBSPOT_STAGE)
Internal status → HubSpot lifecyclestage:

Booked → opportunity
Won't Follow Up → other
Pending → lead
Rejected → subscriber
Internal stage → HubSpot lifecyclestage:

new/contacted/not_interested/call_later/wrong_number → lead
qualified → marketingqualifiedlead
interested → salesqualifiedlead
booked → customer
Error handling
All CRM calls are wrapped in try/except. A CRM failure never blocks the lead status update. _get_client_for_lead() returns None gracefully if HubSpot is not connected.

8. Authentication (Login/JWT)
File: 
auth_routes.py
, 
jwt_handler.py
, 
dependencies.py

Signup (POST /auth/signup)
Checks email uniqueness
Hashes password with bcrypt (passlib, version 4.0.1)
Creates User record with role="user"
Creates two default RetryConfig records: call_later (60 min delay) and no_response (30 min delay)
Returns access token + refresh token immediately
Login (POST /auth/login)
Looks up user by email
Verifies password hash
Checks is_active and is_suspended
Updates last_login
Returns access token + refresh token
Tokens
Access token: JWT, expires in ACCESS_TOKEN_EXPIRE_MINUTES (default: 30 minutes), payload: {sub: user_id, role, type: "access"}
Refresh token: JWT, expires in REFRESH_TOKEN_EXPIRE_DAYS (default: 7 days), payload: {sub: user_id, role, type: "refresh"}
Algorithm: HS256, secret from JWT_SECRET_KEY env var
Token refresh (POST /auth/refresh)
Manual — frontend must call this endpoint with the refresh token. Returns a new access token only (refresh token is not rotated). The frontend client.js does this automatically on any 401 response via tryRefresh().

Auth middleware (app/auth/dependencies.py → get_current_user())
Reads Authorization: Bearer <token> header
Decodes JWT, checks type == "access"
Fetches user from DB, checks is_active and is_suspended
Returns the User object or raises 401/403
9. Live Transcript
Endpoint: GET /calls/leads/{lead_id}/live-transcript in call_routes.py → get_live_transcript()

How it works:

Fetches the most recent CallLog for the lead (ordered by created_at DESC)
Parses log.transcript (raw string) into structured messages by splitting each line on ": " — role before the colon, text after
Normalises role names: bot/assistant/ai → "assistant", user/human/customer → "user"
Returns {lead_id, call_status, transcript: [{role, text}], recording_url, ai_decision, duration_seconds}
Frontend polling (LiveTranscriptModal.jsx):

Polls every 2500ms while call_status is in ["calling", "in-progress", "in_progress", "queued"]
Stops polling automatically when status becomes completed/ended
Auto-scrolls to bottom on new messages
Shows bouncing typing indicator while active
⚠️ True live transcript during an active call is not possible with this architecture. VAPI only sends the full transcript in the end-of-call-report webhook after the call ends. During the call, the transcript field in call_logs is empty. The "Live" button will show an empty transcript window until the call ends.

10. Recording
Source: VAPI generates a recording of every call (if recording is enabled in the VAPI assistant settings). The URL is included in the end-of-call-report webhook payload at artifact.recordingUrl or message.recordingUrl.

Saved: In call_logs.recording_url (VARCHAR 500) by CallLogRepository.update_log() in vapi_webhook.py.

Not saved on the Lead model — only in call_logs.

Frontend playback (LiveTranscriptModal.jsx):

When done && recordingUrl is true, renders an HTML5 <audio controls src={recordingUrl}> player (full width, blue accent color)
Below the player: a "Download" link (<a href={recordingUrl} target="_blank">) that opens the VAPI-hosted MP3 in a new tab
⚠️ If VAPI recording is disabled for the assistant, recording_url will be null and neither the player nor the download button will appear.

11. Dashboard vs Leads Page
Dashboard (
Dashboard.jsx
)
Both admin and regular users see this
Fetches leads via api.leads.list() (regular user) or api.admin.leads.list() (admin) with pagination (PAGE_SIZE=10)
Admin gets a user filter dropdown to see leads for a specific user
Shows: stats cards (total leads, avg score, live AI events), leads table with Call/Live/Recording action buttons, Live AI Events panel (WebSocket), Retry Queue panel
WebSocket connection auto-refreshes the table when ai_decision or call_started events arrive
Leads Page (
Leads.jsx
)
More feature-rich than Dashboard
Full CRUD: View modal, Edit modal (with status override), Delete confirmation, Create Lead modal, CSV Import modal
Advanced filtering: status, stage, score range, search, sort, order
Admin sees an "Owner" column and a user filter dropdown
Same pagination (PAGE_SIZE=10)
Same Live/Recording buttons
Who sees what
Regular users: only their own leads (Lead.filter(user_id=current_user.id))
Admins: all leads with a user_id (orphaned leads with user_id=NULL are excluded)
12. Assistant Management
Creation (POST /assistants/ → assistant_routes.py → create_assistant())
Calls AssistantService.create_assistant(payload, user_id)
AssistantService first calls VapiClient.create_assistant(data) — POSTs to https://api.vapi.ai/assistant with name, firstMessage, model (provider/model/system_prompt), voice
VAPI returns an assistant object with an id
Creates local Assistant record with vapi_assistant_id = vapi_response["id"], scoped to user_id
Update (PUT /assistants/{id} → assistant_routes.py → update_assistant())
Checks ownership
Calls VapiClient.update_assistant() — PATCHes https://api.vapi.ai/assistant/{vapi_id} first
If VAPI fails → raises 502, DB is NOT changed (keeps them in sync)
If VAPI succeeds → updates local DB record
Delete (DELETE /assistants/{id})
Calls VapiClient.delete_assistant() — DELETEs from VAPI (404 is silently ignored)
Always deletes locally regardless of VAPI outcome
Fixed values
Voice is always "Elliot", provider always "openai", model always "gpt-4.1". These are hardcoded constants in Assistants.jsx (FIXED_VOICE, FIXED_PROVIDER, FIXED_MODEL). The edit form shows them as read-only text, not dropdowns.

Assistant selection for calls (
assistant_router.py
)
Not read — this file selects which assistant to use for a given lead. It's called by CallService.start_call().

Bug Diagnosis: Scheduled Call Not Firing + Retry Interval Wrong
Diagnosis Answers
Where is the scheduler defined?
Celery Beat — configured in 
celery_app.py
. The beat_schedule dict defines two periodic tasks:

poll-retry-queue-every-minute — runs poll_retry_queue_task every 60 seconds
sync-hubspot-every-hour — runs sync_hubspot_leads_task at the top of every hour
How are scheduled calls dispatched?
NOT via Celery Beat polling. Scheduled calls use a one-shot apply_async with a countdown. When POST /calls/schedule is called in call_routes.py:

countdown = int((scheduled_at - now).total_seconds())
task = scheduled_call_task.apply_async(args=[sc.id], countdown=countdown)
The task fires exactly once, countdown seconds from now. There is no periodic poller for scheduled calls.