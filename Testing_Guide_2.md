Complete Run & Test Guide
Step 1 — One-time setup
1.1 Install new Python dependency
cd c:\Users\BNC\OneDrive\Documents\Python\workflow_1
.venv\Scripts\activate
pip install passlib[bcrypt]==1.7.4
1.2 Add JWT secret to .env
Open .env and add these lines:

JWT_SECRET_KEY=your-secret-here-run-command-below-to-generate
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
Generate a proper secret:

python -c "import secrets; print(secrets.token_hex(32))"
1.3 Run both migration SQL files against Supabase
Open your Supabase dashboard → SQL Editor → run each file in order:

File 1: 
add_auth_system.sql
 File 2: 
add_advanced_features.sql

After running, verify:

SELECT email, role FROM users;
-- Should show: admin@example.com | admin

SELECT outcome_type, retry_delay_minutes FROM retry_configs;
-- Should show: call_later=60, no_response=30
Step 2 — Start all services
Open 4 separate terminals:

Terminal 1 — FastAPI backend:

cd c:\Users\BNC\OneDrive\Documents\Python\workflow_1
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
Watch for startup log:

STARTUP — environment variable check
  VAPI_API_KEY        : dec8eea5-4c8...
  JWT_SECRET_KEY      : <your-key>...
Terminal 2 — Celery worker + beat scheduler:

cd c:\Users\BNC\OneDrive\Documents\Python\workflow_1
.venv\Scripts\activate
celery -A app.queues.celery_app worker --beat --loglevel=info
Terminal 3 — Redis (if not running as a service):

redis-server
Terminal 4 — React frontend:

cd c:\Users\BNC\OneDrive\Documents\Python\workflow_1\front-end
npm run dev
Open browser: http://localhost:5173

Step 3 — First login
Default admin credentials (set in migration SQL):

Email: admin@example.com
Password: Admin@1234
Change this password immediately after first login via Admin → Users → Reset Password.

Step 4 — Test each feature
4.1 Authentication
# Signup a new user
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test@1234","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"Admin@1234"}'
# → Copy the access_token from response

# Verify token works
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
4.2 HubSpot Sync
TOKEN="paste-your-token-here"

# Sync contacts
curl -X POST http://localhost:8000/hubspot/sync \
  -H "Authorization: Bearer $TOKEN"
# → {"total_contacts":N,"created":N,"updated":N,"errors":0}
Verify in Supabase:

SELECT COUNT(*), user_id FROM leads GROUP BY user_id;
-- All leads should have user_id = 1 (admin)
4.3 Retry Config
# View current config
curl http://localhost:8000/retry-configs/ \
  -H "Authorization: Bearer $TOKEN"

# Update call_later delay to 15 minutes
curl -X PUT http://localhost:8000/retry-configs/call_later \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"retry_delay_minutes":15,"max_retry_attempts":3}'
In the frontend: Settings → Retry Timing — move the slider and click Save.

4.4 CSV Import
# Download template first
curl http://localhost:8000/leads/download-template \
  -H "Authorization: Bearer $TOKEN" \
  -o leads_template.csv

# Upload a CSV
curl -X POST http://localhost:8000/leads/upload-csv \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@leads_template.csv"
# → {"imported":2,"skipped":0,"errors":[]}
In the frontend: Leads → Import CSV button.

4.5 Lead Filtering
# Filter by status
curl "http://localhost:8000/leads/?status=Booked" \
  -H "Authorization: Bearer $TOKEN"

# Filter by score range
curl "http://localhost:8000/leads/?score_min=50&score_max=100&sort=score&order=desc" \
  -H "Authorization: Bearer $TOKEN"

# Search
curl "http://localhost:8000/leads/?search=johnson" \
  -H "Authorization: Bearer $TOKEN"
In the frontend: Leads → Filters button.

4.6 Call Scheduling
# Schedule a call 5 minutes from now
FUTURE=$(python -c "from datetime import datetime,timezone,timedelta; print((datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat())")

curl -X POST http://localhost:8000/calls/schedule \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"lead_id\":1,\"assistant_id\":1,\"scheduled_at\":\"$FUTURE\"}"

# List scheduled calls
curl http://localhost:8000/calls/scheduled \
  -H "Authorization: Bearer $TOKEN"

# Cancel
curl -X DELETE http://localhost:8000/calls/scheduled/1 \
  -H "Authorization: Bearer $TOKEN"
In the frontend: Scheduled → Schedule Call button.

4.7 CRM Connection (per-user)
# Connect HubSpot with your API key
curl -X POST http://localhost:8000/crm/connect \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"crm_type":"hubspot","api_key":"pat-na2-YOUR-KEY"}'

# Sync using user's own key
curl -X POST http://localhost:8000/crm/sync \
  -H "Authorization: Bearer $TOKEN"
In the frontend: Settings → CRM Connections → Connect CRM.

4.8 Notification Preferences
# View
curl http://localhost:8000/users/notification-settings \
  -H "Authorization: Bearer $TOKEN"

# Update
curl -X PUT http://localhost:8000/users/notification-settings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email_on_interested":true,"email_on_call_completed":false,"email_on_retry_failed":true}'
In the frontend: Settings → Email Notifications toggles.

4.9 Admin features
# List all users
curl http://localhost:8000/admin/users \
  -H "Authorization: Bearer $TOKEN"

# Global analytics
curl http://localhost:8000/admin/analytics/global \
  -H "Authorization: Bearer $TOKEN"

# All assistants across users
curl http://localhost:8000/admin/assistants/all \
  -H "Authorization: Bearer $TOKEN"
In the frontend: Admin → Users and Admin → Analytics (only visible when logged in as admin).

4.10 Multi-tenancy isolation test
# Login as regular user
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test@1234"}'
# → Copy USER_TOKEN

# This user should see 0 leads (they have none)
curl http://localhost:8000/leads/ \
  -H "Authorization: Bearer USER_TOKEN"
# → {"total":0,"leads":[]}

# Trying to call admin's lead should return 403
curl -X POST http://localhost:8000/calls/start/1 \
  -H "Authorization: Bearer USER_TOKEN"
# → {"detail":"Access denied"}
Step 5 — Verify Celery Beat is working
After starting the worker, check logs every 60 seconds for:

INFO | POLL RETRY QUEUE: checking for overdue retries
INFO | POLL RETRY QUEUE: found 0 overdue retries
To force a retry to fire immediately:

UPDATE retry_queue
SET retry_at = NOW() - INTERVAL '1 minute'
WHERE retry_status = 'pending'
LIMIT 1;
Within 60 seconds you should see:

INFO | POLL RETRY QUEUE: found 1 overdue retries
INFO | POLL RETRY QUEUE: dispatched call for lead X
Complete Feature Checklist
Feature	Backend	Frontend	Test
JWT Login / Signup	✅	✅ /login /signup	curl + browser
Token refresh on 401	✅	✅ auto	automatic
Multi-tenancy isolation	✅	✅	curl with 2 users
Admin user management	✅	✅ /admin/users	browser
Admin analytics	✅	✅ /admin/analytics	browser
Dynamic retry timing	✅	✅ Settings page	slider + save
Per-user CRM connection	✅	✅ Settings page	connect + sync
CSV lead import	✅	✅ Leads page	upload button
Lead filtering + search	✅	✅ Leads page	filter panel
Call scheduling	✅	✅ Scheduled page	schedule modal
Notification preferences	✅	✅ Settings page	toggles
Recording URL stored	✅	✅ via API	VAPI webhook
Activity logging	✅	—	check DB
Celery Beat retry poller	✅	—	force overdue SQL
Troubleshooting
Problem	Fix
401 Unauthorized on all requests	Check JWT_SECRET_KEY is in .env and server restarted
passlib import error	Run pip install passlib[bcrypt]==1.7.4
Login returns 403 Account is suspended	Run UPDATE users SET is_suspended=false WHERE email='admin@example.com'
CSV upload fails with column error	Download the template first, use exact column names
Scheduled call doesn't fire	Ensure Celery worker is running with --beat flag
Frontend shows blank page	Check browser console — likely a missing import or route
No CRM connected on sync	Connect CRM first via Settings → CRM Connections
Retry config not found	Run add_advanced_features.sql migration — it creates defaults