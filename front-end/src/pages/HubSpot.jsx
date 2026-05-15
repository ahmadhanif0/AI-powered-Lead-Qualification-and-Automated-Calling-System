import { useState } from "react";
import { RefreshCw, Download, Zap, Users, AlertCircle, CheckCircle } from "lucide-react";
import { api } from "../api/client";
import { Spinner } from "../components/Spinner";
import { useToast } from "../components/Toast";

// ── Result Banner ────────────────────────────────────────────────────
function ResultBanner({ result }) {
  if (!result) return null;
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 space-y-3">
      <div className="flex items-center gap-2 text-green-400 font-semibold">
        <CheckCircle size={16} /> Sync Complete
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Total Contacts", value: result.total_contacts, color: "text-blue-400" },
          { label: "Created",        value: result.created,        color: "text-green-400" },
          { label: "Updated",        value: result.updated,        color: "text-yellow-400" },
          { label: "Errors",         value: result.errors,         color: result.errors > 0 ? "text-red-400" : "text-gray-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-gray-900 rounded-lg p-3 text-center">
            <div className={`text-2xl font-bold ${color}`}>{value ?? "—"}</div>
            <div className="text-xs text-gray-500 mt-1">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Contact Preview Table ────────────────────────────────────────────
function ContactsTable({ contacts }) {
  if (!contacts || contacts.length === 0) return null;
  return (
    <div className="bg-gray-900 rounded-xl overflow-x-auto">
      <div className="p-4 border-b border-gray-800 font-semibold flex items-center gap-2 text-sm">
        <Users size={15} /> Contacts Preview
        <span className="text-gray-500 font-normal">({contacts.length})</span>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-gray-500 border-b border-gray-800">
            <th className="text-left p-3">Name</th>
            <th className="text-left p-3">Email</th>
            <th className="text-left p-3">Phone</th>
            <th className="text-left p-3">Company</th>
            <th className="text-left p-3">Stage</th>
          </tr>
        </thead>
        <tbody>
          {contacts.slice(0, 50).map((c) => {
            const p = c.properties || {};
            return (
              <tr key={c.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                <td className="p-3">{[p.firstname, p.lastname].filter(Boolean).join(" ") || "—"}</td>
                <td className="p-3 text-gray-400 text-xs">{p.email || "—"}</td>
                <td className="p-3 text-gray-400 text-xs">{p.phone || "—"}</td>
                <td className="p-3 text-gray-300">{p.company || "—"}</td>
                <td className="p-3 text-gray-400 text-xs capitalize">{p.lifecyclestage || "—"}</td>
              </tr>
            );
          })}
          {contacts.length > 50 && (
            <tr>
              <td colSpan={5} className="p-3 text-center text-gray-500 text-xs">
                … and {contacts.length - 50} more
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── HubSpot Page ─────────────────────────────────────────────────────
export default function HubSpot() {
  const [contacts,    setContacts]    = useState(null);
  const [syncResult,  setSyncResult]  = useState(null);
  const [loadingFetch, setLoadingFetch] = useState(false);
  const [loadingSync,  setLoadingSync]  = useState(false);
  const [loadingAsync, setLoadingAsync] = useState(false);
  const [error,        setError]        = useState(null);
  const { show, ToastEl } = useToast();

  async function fetchContacts() {
    setLoadingFetch(true);
    setError(null);
    try {
      const data = await api.hubspot.contacts();
      setContacts(data.contacts || []);
      show(`Fetched ${data.total} contacts`);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingFetch(false);
    }
  }

  async function syncNow() {
    setLoadingSync(true);
    setError(null);
    setSyncResult(null);
    try {
      const result = await api.hubspot.sync();
      setSyncResult(result);
      show("Sync completed");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingSync(false);
    }
  }

  async function syncAsync() {
    setLoadingAsync(true);
    setError(null);
    try {
      const data = await api.hubspot.syncAsync();
      show(`Background sync started — task ${data.task_id}`);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingAsync(false);
    }
  }

  return (
    <div className="space-y-6">
      {ToastEl}

      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">HubSpot</h1>
      </div>

      {/* Action cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Fetch contacts */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-blue-400">
            <Download size={18} />
            <span className="font-semibold text-sm">Fetch Contacts</span>
          </div>
          <p className="text-xs text-gray-500">Preview all HubSpot contacts without saving to database.</p>
          <button
            onClick={fetchContacts}
            disabled={loadingFetch}
            className="w-full py-2 rounded bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            {loadingFetch ? <Spinner size={14} /> : <Download size={14} />}
            {loadingFetch ? "Fetching…" : "Fetch Contacts"}
          </button>
        </div>

        {/* Sync now */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-green-400">
            <RefreshCw size={18} />
            <span className="font-semibold text-sm">Sync Now</span>
          </div>
          <p className="text-xs text-gray-500">Sync contacts to database immediately. Waits for completion.</p>
          <button
            onClick={syncNow}
            disabled={loadingSync}
            className="w-full py-2 rounded bg-green-700 hover:bg-green-600 disabled:opacity-50 text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            {loadingSync ? <Spinner size={14} /> : <RefreshCw size={14} />}
            {loadingSync ? "Syncing…" : "Sync Now"}
          </button>
        </div>

        {/* Async sync */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-yellow-400">
            <Zap size={18} />
            <span className="font-semibold text-sm">Background Sync</span>
          </div>
          <p className="text-xs text-gray-500">Queue sync as a Celery background task. Returns immediately.</p>
          <button
            onClick={syncAsync}
            disabled={loadingAsync}
            className="w-full py-2 rounded bg-yellow-700 hover:bg-yellow-600 disabled:opacity-50 text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            {loadingAsync ? <Spinner size={14} /> : <Zap size={14} />}
            {loadingAsync ? "Queuing…" : "Background Sync"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2 text-red-400 bg-red-900/20 border border-red-800 rounded-lg p-4 text-sm">
          <AlertCircle size={16} className="shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* Sync result */}
      <ResultBanner result={syncResult} />

      {/* Contacts preview */}
      <ContactsTable contacts={contacts} />
    </div>
  );
}
