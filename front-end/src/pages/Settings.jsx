import { useState, useEffect, useCallback } from "react";
import {
  Settings as SettingsIcon, Bell, Clock, Database,
  RefreshCw, CheckCircle, AlertCircle, Link2, Link,
} from "lucide-react";
import { api }                  from "../api/client";
import { Spinner }              from "../components/Spinner";
import { useToast }             from "../components/Toast";
import { DeleteConfirmModal }   from "../components/DeleteConfirmModal";

// ── Toggle Switch ─────────────────────────────────────────────────────
function Toggle({ checked, onChange, label, description }) {
  return (
    <div className="flex items-start justify-between py-3 border-b border-gray-800 last:border-0">
      <div>
        <div className="text-sm font-medium">{label}</div>
        {description && <div className="text-xs text-gray-500 mt-0.5">{description}</div>}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative w-10 h-5 rounded-full transition-colors shrink-0 ml-4 ${checked ? "bg-blue-600" : "bg-gray-600"}`}
      >
        <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${checked ? "translate-x-5" : "translate-x-0.5"}`} />
      </button>
    </div>
  );
}

// ── Delay Slider ──────────────────────────────────────────────────────
function DelaySlider({ label, value, onChange, min = 5, max = 1440 }) {
  const hours   = Math.floor(value / 60);
  const mins    = value % 60;
  const display = hours > 0 ? `${hours}h ${mins > 0 ? `${mins}m` : ""}`.trim() : `${mins}m`;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-gray-300">{label}</span>
        <span className="text-blue-400 font-medium">{display}</span>
      </div>
      <input type="range" min={min} max={max} step={5} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-blue-500" />
      <div className="flex justify-between text-xs text-gray-600">
        <span>5m</span><span>6h</span><span>12h</span><span>24h</span>
      </div>
    </div>
  );
}

// ── HubSpot OAuth Panel ───────────────────────────────────────────────
function HubSpotOAuthPanel({ show: showToast }) {
  const [status,        setStatus]        = useState(null);
  const [loading,       setLoading]       = useState(true);
  const [connecting,    setConnecting]    = useState(false);
  const [refreshing,    setRefreshing]    = useState(false);
  const [syncing,       setSyncing]       = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [showDisconnectModal, setShowDisconnectModal] = useState(false);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    try {
      const s = await api.hubspot.oauth.status();
      setStatus(s);
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setLoading(false);
    }
  }, []);

  // On mount: load status + handle OAuth callback redirect
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const hs     = params.get("hubspot");
    if (hs === "connected") {
      showToast("HubSpot connected successfully!");
      // Clean the URL
      window.history.replaceState({}, "", window.location.pathname);
    } else if (hs === "error") {
      showToast("HubSpot connection failed — check your app credentials.", "error");
      window.history.replaceState({}, "", window.location.pathname);
    }
    loadStatus();
  }, [loadStatus]);

  async function handleConnect() {
    setConnecting(true);
    try {
      const data = await api.hubspot.oauth.connect();
      // Redirect browser to HubSpot authorization page
      window.location.href = data.authorization_url;
    } catch (e) {
      showToast(e.message, "error");
      setConnecting(false);
    }
  }

  async function handleRefreshToken() {
    setRefreshing(true);
    try {
      await api.hubspot.oauth.refreshToken();
      showToast("Token refreshed successfully");
      loadStatus();
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setRefreshing(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    try {
      // Use synchronous sync (POST /hubspot/sync) — waits for completion
      // and returns actual counts. syncAsync queues a Celery task which
      // can't access the user's OAuth token in the worker context.
      const r = await api.hubspot.sync();
      showToast(
        `Leads synced — ${r.created} created, ${r.updated} updated` +
        (r.errors > 0 ? `, ${r.errors} errors` : "")
      );
      // Refresh status to update last_sync_at timestamp
      loadStatus();
    } catch (e) {
      showToast(e.message || "Sync failed. Please try again.", "error");
    } finally {
      setSyncing(false);
    }
  }

  // Opens the confirmation modal — actual API call in handleDisconnectConfirm
  function handleDisconnect() {
    setShowDisconnectModal(true);
  }

  async function handleDisconnectConfirm() {
    setDisconnecting(true);
    try {
      await api.hubspot.oauth.disconnect();
      setShowDisconnectModal(false);
      showToast("HubSpot disconnected");
      loadStatus();
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setDisconnecting(false);
    }
  }

  const connected = status?.is_connected;
  const expired   = status?.is_expired;

  if (loading) return <div className="flex justify-center py-6"><Spinner /></div>;

  return (
    <div className="space-y-4">
      {/* Connection status banner */}
      {connected && !expired ? (
        <div className="flex items-center gap-2 text-green-400 text-sm">
          <CheckCircle size={16} /> Connected to HubSpot
          {status.portal_id && (
            <span className="text-gray-500 text-xs ml-1">· Portal {status.portal_id}</span>
          )}
        </div>
      ) : expired ? (
        <div className="flex items-center gap-2 text-amber-400 text-sm bg-amber-900/20 border border-amber-800/40 rounded-lg p-3">
          <AlertCircle size={15} />
          Token expired — refresh it or reconnect.
        </div>
      ) : (
        <p className="text-gray-400 text-sm">
          Connect your HubSpot account to sync contacts as leads automatically.
          Each user connects their own HubSpot account.
        </p>
      )}

      {/* Last sync */}
      {status?.last_sync_at && (
        <p className="text-xs text-gray-500">
          Last sync: {new Date(status.last_sync_at).toLocaleString()}
        </p>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        {!connected || expired ? (
          <button
            onClick={handleConnect}
            disabled={connecting}
            className="flex items-center gap-2 px-4 py-2 rounded bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-sm font-medium transition-colors"
          >
            {connecting ? <Spinner size={14} /> : <Link2 size={14} />}
            {connecting ? "Redirecting…" : "Connect HubSpot"}
          </button>
        ) : (
          <>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-2 px-3 py-1.5 rounded bg-green-700 hover:bg-green-600 disabled:opacity-50 text-xs font-medium transition-colors"
            >
              {syncing ? <Spinner size={12} /> : <RefreshCw size={12} />}
              {syncing ? "Syncing leads…" : "Sync Now"}
            </button>

            <button
              onClick={handleRefreshToken}
              disabled={refreshing}
              className="flex items-center gap-2 px-3 py-1.5 rounded bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-xs font-medium transition-colors"
            >
              {refreshing ? <Spinner size={12} /> : <RefreshCw size={12} />}
              {refreshing ? "Refreshing…" : "Refresh Token"}
            </button>

            <button
              onClick={handleDisconnect}
              disabled={disconnecting}
              className="flex items-center gap-2 px-3 py-1.5 rounded bg-red-800 hover:bg-red-700 disabled:opacity-50 text-xs transition-colors"
            >
              {disconnecting ? <Spinner size={12} /> : <Link size={12} />}
              Disconnect
            </button>
          </>
        )}
      </div>

      {/* Setup instructions (shown when not connected) */}
      {!connected && (
        <details className="text-xs text-gray-500 border border-gray-800 rounded-lg p-3 cursor-pointer">
          <summary className="font-medium text-gray-400 cursor-pointer">
            How to set up HubSpot OAuth
          </summary>
          <ol className="mt-2 space-y-1 list-decimal list-inside leading-relaxed">
            <li>Go to <a href="https://developers.hubspot.com" target="_blank" rel="noreferrer" className="text-blue-400 underline">developers.hubspot.com</a></li>
            <li>Create a Legacy App → copy Client ID and Client Secret</li>
            <li>Set Redirect URL to <code className="bg-gray-800 px-1 rounded">http://localhost:8000/crm/hubspot/callback</code></li>
            <li>Add scopes: <code className="bg-gray-800 px-1 rounded">crm.objects.contacts.read/write</code></li>
            <li>Add <code className="bg-gray-800 px-1 rounded">HUBSPOT_CLIENT_ID</code>, <code className="bg-gray-800 px-1 rounded">HUBSPOT_CLIENT_SECRET</code>, <code className="bg-gray-800 px-1 rounded">HUBSPOT_REDIRECT_URI</code> to your <code className="bg-gray-800 px-1 rounded">.env</code></li>
            <li>Restart the backend, then click Connect HubSpot above</li>
          </ol>
        </details>
      )}

      {/* Disconnect confirmation modal */}
      <DeleteConfirmModal
        open={showDisconnectModal}
        onClose={() => !disconnecting && setShowDisconnectModal(false)}
        onConfirm={handleDisconnectConfirm}
        title="Disconnect HubSpot?"
        itemName={status?.portal_id ? `Portal ${status.portal_id}` : "HubSpot Account"}
        warning="This will remove your HubSpot connection. Your existing leads will remain, but no new syncs will run until you reconnect."
        isDeleting={disconnecting}
      />
    </div>
  );
}

// ── Settings Page ─────────────────────────────────────────────────────
export default function Settings() {
  const { show, ToastEl } = useToast();

  // Notification prefs
  const [notifPrefs,  setNotifPrefs]  = useState(null);
  const [savingNotif, setSavingNotif] = useState(false);

  // Retry configs
  const [savingRetry,     setSavingRetry]     = useState(false);
  const [callLaterDelay,  setCallLaterDelay]  = useState(60);
  const [noResponseDelay, setNoResponseDelay] = useState(30);
  const [callLaterMax,    setCallLaterMax]    = useState(3);
  const [noResponseMax,   setNoResponseMax]   = useState(3);

  const loadAll = useCallback(async () => {
    try {
      const [notif, retry] = await Promise.all([
        api.users.notificationSettings(),
        api.retryConfigs.list(),
      ]);
      setNotifPrefs(notif);

      const cl = retry.find(r => r.outcome_type === "call_later");
      const nr = retry.find(r => r.outcome_type === "no_response");
      if (cl) { setCallLaterDelay(cl.retry_delay_minutes); setCallLaterMax(cl.max_retry_attempts); }
      if (nr) { setNoResponseDelay(nr.retry_delay_minutes); setNoResponseMax(nr.max_retry_attempts); }
    } catch (e) { show(e.message, "error"); }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  async function saveNotifPrefs() {
    setSavingNotif(true);
    try {
      await api.users.updateNotificationSettings(notifPrefs);
      show("Notification preferences saved");
    } catch (e) { show(e.message, "error"); }
    finally { setSavingNotif(false); }
  }

  async function saveRetryConfigs() {
    setSavingRetry(true);
    try {
      await Promise.all([
        api.retryConfigs.update("call_later",  { retry_delay_minutes: callLaterDelay,  max_retry_attempts: callLaterMax }),
        api.retryConfigs.update("no_response", { retry_delay_minutes: noResponseDelay, max_retry_attempts: noResponseMax }),
      ]);
      show("Retry settings saved");
    } catch (e) { show(e.message, "error"); }
    finally { setSavingRetry(false); }
  }

  const MAX_OPTIONS = [1, 2, 3, 5];
  const selCls = "bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500";

  return (
    <div className="max-w-2xl space-y-6">
      {ToastEl}
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <SettingsIcon size={22} /> Settings
      </h1>

      {/* ── HubSpot OAuth ── */}
      <div className="bg-gray-900 rounded-xl p-5">
        <h2 className="font-semibold mb-4 flex items-center gap-2 text-sm text-gray-400 uppercase tracking-wide">
          <Database size={15} /> HubSpot Integration
        </h2>
        <HubSpotOAuthPanel show={show} />
      </div>

      {/* ── Notification Preferences ── */}
      <div className="bg-gray-900 rounded-xl p-5">
        <h2 className="font-semibold mb-4 flex items-center gap-2 text-sm text-gray-400 uppercase tracking-wide">
          <Bell size={15} /> Email Notifications
        </h2>
        {!notifPrefs ? (
          <div className="flex justify-center py-4"><Spinner /></div>
        ) : (
          <>
            <Toggle
              checked={notifPrefs.email_on_interested}
              onChange={(v) => setNotifPrefs(p => ({ ...p, email_on_interested: v }))}
              label="Lead is Interested"
              description="Send email when AI detects an interested lead"
            />
            <Toggle
              checked={notifPrefs.email_on_call_completed}
              onChange={(v) => setNotifPrefs(p => ({ ...p, email_on_call_completed: v }))}
              label="Call Completed"
              description="Send email after every completed call"
            />
            <Toggle
              checked={notifPrefs.email_on_retry_failed}
              onChange={(v) => setNotifPrefs(p => ({ ...p, email_on_retry_failed: v }))}
              label="Retry Failed"
              description="Send email when a retry call fails permanently"
            />
            <button onClick={saveNotifPrefs} disabled={savingNotif}
              className="mt-4 px-4 py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium flex items-center gap-2">
              {savingNotif ? <Spinner size={14} /> : null} Save Preferences
            </button>
          </>
        )}
      </div>

      {/* ── Retry Timing ── */}
      <div className="bg-gray-900 rounded-xl p-5">
        <h2 className="font-semibold mb-4 flex items-center gap-2 text-sm text-gray-400 uppercase tracking-wide">
          <Clock size={15} /> Retry Timing
        </h2>
        <div className="space-y-5">
          <DelaySlider label="Call Later — retry after" value={callLaterDelay} onChange={setCallLaterDelay} />
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Max attempts (Call Later)</span>
            <select className={selCls} value={callLaterMax} onChange={e => setCallLaterMax(Number(e.target.value))}>
              {MAX_OPTIONS.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <DelaySlider label="No Response — retry after" value={noResponseDelay} onChange={setNoResponseDelay} />
            <div className="flex items-center justify-between text-sm mt-4">
              <span className="text-gray-400">Max attempts (No Response)</span>
              <select className={selCls} value={noResponseMax} onChange={e => setNoResponseMax(Number(e.target.value))}>
                {MAX_OPTIONS.map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
          </div>

          <button onClick={saveRetryConfigs} disabled={savingRetry}
            className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium flex items-center gap-2">
            {savingRetry ? <Spinner size={14} /> : null} Save Retry Settings
          </button>
        </div>
      </div>
    </div>
  );
}
