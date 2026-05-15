import { useEffect, useState } from "react";
import { Users, TrendingUp, Zap, Phone, Search, RefreshCw, Activity, Clock, AlertCircle } from "lucide-react";
import { useLeads }    from "../hooks/useLeads";
import { useRetries }  from "../hooks/useRetries";
import { useWebSocket } from "../hooks/useWebSocket";
import { Spinner }     from "../components/Spinner";
import { Modal }       from "../components/Modal";
import { useToast }    from "../components/Toast";
import {
  leadStatusColor, callStatusColor, callStatusLabel,
  decisionColor, formatRetryTime,
} from "../lib/helpers";

// ── Start Call Modal ─────────────────────────────────────────────────
function StartCallModal({ lead, onClose, onSuccess }) {
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const { startCall } = useLeads();

  async function handleCall() {
    setLoading(true);
    setError(null);
    try {
      await startCall(lead.id);
      onSuccess(`Call started for ${lead.name || `Lead #${lead.id}`}`);
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Start AI Call">
      <div className="space-y-4">
        <div className="bg-gray-800 rounded-lg p-4 space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Lead</span>
            <span className="font-medium">{lead.name || `#${lead.id}`}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Phone</span>
            <span>{lead.phone || "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Company</span>
            <span>{lead.company || "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Score</span>
            <span className="text-green-400 font-bold">{Math.round(lead.score ?? 0)}</span>
          </div>
        </div>

        {!lead.phone && (
          <p className="text-yellow-400 text-xs bg-yellow-900/30 border border-yellow-800 rounded p-2">
            ⚠ This lead has no phone number. The call may fail.
          </p>
        )}

        {error && (
          <p className="text-red-400 text-xs bg-red-900/30 border border-red-800 rounded p-2">
            {error}
          </p>
        )}

        <div className="flex gap-3 pt-1">
          <button
            onClick={onClose}
            className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCall}
            disabled={loading}
            className="flex-1 py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            {loading ? <Spinner size={14} /> : <Phone size={14} />}
            {loading ? "Calling…" : "Start Call"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ── Dashboard Page ───────────────────────────────────────────────────
export default function Dashboard() {
  const { leads, loading, error, reload: reloadLeads } = useLeads();
  const { retries, reload: reloadRetries }             = useRetries();
  const [search,   setSearch]   = useState("");
  const [callLead, setCallLead] = useState(null);
  const [now,      setNow]      = useState(Date.now());
  const { show, ToastEl }       = useToast();

  // Live countdown ticker
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  // WebSocket — refresh tables on live events
  const { events, wsStatus } = useWebSocket((msg) => {
    if (msg.event === "ai_decision" || msg.event === "call_started") {
      reloadLeads();
      reloadRetries();
    }
  });

  const filtered = leads.filter((l) =>
    (l.name    || "").toLowerCase().includes(search.toLowerCase()) ||
    (l.email   || "").toLowerCase().includes(search.toLowerCase()) ||
    (l.company || "").toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total:       leads.length,
    avgScore:    leads.length ? Math.round(leads.reduce((s, l) => s + (l.score || 0), 0) / leads.length) : 0,
    aiDecisions: events.filter((e) => e.event === "ai_decision").length,
  };

  return (
    <div className="space-y-6">
      {ToastEl}

      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-4 text-sm">
          <button
            onClick={() => { reloadLeads(); reloadRetries(); }}
            className="flex items-center gap-1 text-gray-400 hover:text-white transition-colors"
          >
            <RefreshCw size={14} /> Refresh
          </button>
          <span className="text-gray-500">
            WS:{" "}
            <span className={wsStatus === "connected" ? "text-green-400" : "text-red-400"}>
              {wsStatus}
            </span>
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: Users,     color: "text-blue-400",   label: "Total Leads",       value: stats.total },
          { icon: TrendingUp,color: "text-green-400",  label: "Avg Score",         value: stats.avgScore },
          { icon: Zap,       color: "text-yellow-400", label: "AI Decisions (live)",value: stats.aiDecisions },
        ].map(({ icon: Icon, color, label, value }) => (
          <div key={label} className="bg-gray-900 p-4 rounded-lg flex items-center gap-3">
            <Icon className={color} size={22} />
            <div>
              <div className="text-xs text-gray-400">{label}</div>
              <div className="text-xl font-bold">{value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          className="w-full pl-8 py-2 pr-3 bg-gray-800 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-600"
          placeholder="Search by name, email or company…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Leads Table */}
      <div className="bg-gray-900 rounded overflow-x-auto">
        <div className="p-4 border-b border-gray-800 font-bold flex items-center gap-2">
          <Users size={16} /> Leads
          <span className="text-xs text-gray-500 font-normal ml-1">({filtered.length})</span>
        </div>

        {loading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : error ? (
          <div className="p-6 text-center text-red-400 text-sm">{error}</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-gray-800">
                <th className="text-left p-3">Name</th>
                <th className="text-left p-3">Company</th>
                <th className="text-left p-3">Email</th>
                <th className="text-left p-3">Score</th>
                <th className="text-left p-3">Stage</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Call Status</th>
                <th className="text-left p-3">AI Decision</th>
                <th className="text-left p-3">Retries</th>
                <th className="text-left p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={10} className="p-6 text-center text-gray-500">No leads found</td></tr>
              ) : filtered.map((l) => (
                <tr key={l.id} className="border-b border-gray-800 hover:bg-gray-800/60 transition-colors">
                  <td className="p-3">
                    <div className="font-medium">{l.name || "—"}</div>
                    <div className="text-xs text-gray-500">{l.phone || ""}</div>
                  </td>
                  <td className="p-3 text-gray-300">{l.company || "—"}</td>
                  <td className="p-3 text-gray-400 text-xs">{l.email || "—"}</td>
                  <td className="p-3 text-green-400 font-bold">{l.score != null ? Math.round(l.score) : "—"}</td>
                  <td className="p-3 text-gray-400 text-xs capitalize">{l.stage || "—"}</td>
                  <td className={`p-3 text-xs font-semibold ${leadStatusColor(l.status)}`}>{l.status || "—"}</td>
                  <td className={`p-3 text-xs font-medium ${callStatusColor(l.call_status)}`}>{callStatusLabel(l.call_status)}</td>
                  <td className={`p-3 text-xs font-medium ${decisionColor(l.ai_decision)}`}>{l.ai_decision || "—"}</td>
                  <td className="p-3 text-gray-400 text-xs">{l.retry_count > 0 ? `×${l.retry_count}` : "—"}</td>
                  <td className="p-3">
                    <button
                      onClick={() => setCallLead(l)}
                      className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-blue-700 hover:bg-blue-600 transition-colors"
                    >
                      <Phone size={11} /> Call
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Live Events + Retry Queue side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Live AI Events */}
        <div className="bg-gray-900 p-4 rounded">
          <h2 className="mb-3 font-bold flex items-center gap-2 text-sm">
            <Activity size={15} /> Live AI Events
          </h2>
          {events.length === 0 ? (
            <p className="text-gray-500 text-sm">No events yet</p>
          ) : (
            <div className="space-y-0 max-h-64 overflow-y-auto">
              {events.map((e, i) => (
                <div key={i} className="text-sm flex items-start gap-3 border-b border-gray-800 py-2">
                  <span className="text-cyan-400 text-xs w-28 shrink-0">{e.event}</span>
                  {e.decision && (
                    <span className={`font-medium text-xs ${decisionColor(e.decision)}`}>→ {e.decision}</span>
                  )}
                  {e.lead_id && <span className="text-gray-500 text-xs">#{e.lead_id}</span>}
                  <span className="text-gray-600 text-xs ml-auto">{new Date().toLocaleTimeString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Retry Queue */}
        <div className="bg-gray-900 p-4 rounded">
          <h2 className="mb-3 font-bold flex items-center gap-2 text-sm">
            <Clock size={15} /> Retry Queue
            {retries.length > 0 && (
              <span className="text-xs bg-yellow-600 text-white px-2 py-0.5 rounded-full">{retries.length}</span>
            )}
          </h2>
          {retries.length === 0 ? (
            <p className="text-gray-500 text-sm">No pending retries</p>
          ) : (
            <div className="space-y-0 max-h-64 overflow-y-auto">
              {retries.map((r) => {
                const isOverdue = r.retry_at && new Date(r.retry_at) < new Date();
                return (
                  <div key={r.id} className="text-sm flex items-center justify-between border-b border-gray-800 py-2">
                    <div className="flex items-center gap-2">
                      {isOverdue
                        ? <AlertCircle size={13} className="text-red-400" />
                        : <Clock size={13} className="text-yellow-400" />}
                      <span className="text-xs">Lead <span className="text-white font-medium">#{r.lead_id}</span></span>
                      <span className="text-gray-400 text-xs capitalize">{r.retry_reason || "—"}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                        r.retry_status === "processing" ? "bg-blue-800 text-blue-200"
                        : r.retry_status === "failed"   ? "bg-red-800 text-red-200"
                        : "bg-gray-700 text-gray-300"}`}>
                        {r.retry_status}
                      </span>
                    </div>
                    <span className={`text-xs ${isOverdue ? "text-red-400" : "text-gray-400"}`}>
                      {formatRetryTime(r.retry_at)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Start Call Modal */}
      {callLead && (
        <StartCallModal
          lead={callLead}
          onClose={() => setCallLead(null)}
          onSuccess={(msg) => { show(msg); reloadLeads(); }}
        />
      )}
    </div>
  );
}
