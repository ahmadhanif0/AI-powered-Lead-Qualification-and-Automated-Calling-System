import { useState, useEffect, useCallback } from "react";
import { Calendar, Plus, Trash2, RefreshCw, Clock } from "lucide-react";
import { api }        from "../api/client";
import { Spinner }    from "../components/Spinner";
import { Modal }      from "../components/Modal";
import { EmptyState } from "../components/EmptyState";
import { useToast }   from "../components/Toast";

function secondsToDisplay(s) {
  if (s <= 0) return "Now";
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${sec}s`;
  return `${sec}s`;
}

// ── Schedule Call Modal ───────────────────────────────────────────────
function ScheduleModal({ onClose, onScheduled }) {
  const [leads,      setLeads]      = useState([]);
  const [assistants, setAssistants] = useState([]);
  const [form,       setForm]       = useState({ lead_id: "", assistant_id: "", scheduled_at: "" });
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState(null);

  useEffect(() => {
    Promise.all([api.leads.list({ page_size: 200 }), api.assistants.list()])
      .then(([l, a]) => { setLeads(l.leads || []); setAssistants(a.assistants || []); })
      .catch(console.error);
  }, []);

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      await api.calls.schedule({
        lead_id:      parseInt(form.lead_id),
        assistant_id: parseInt(form.assistant_id),
        scheduled_at: new Date(form.scheduled_at).toISOString(),
      });
      onScheduled();
      onClose();
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  const inp = "w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500";
  // Min datetime = now + 1 minute
  const minDt = new Date(Date.now() + 60000).toISOString().slice(0, 16);

  return (
    <Modal open onClose={onClose} title="Schedule a Call">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Lead <span className="text-red-400">*</span></label>
          <select className={inp} value={form.lead_id} onChange={set("lead_id")} required>
            <option value="">— select lead —</option>
            {leads.map(l => <option key={l.id} value={l.id}>{l.name || `Lead #${l.id}`} {l.phone ? `· ${l.phone}` : ""}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Assistant <span className="text-red-400">*</span></label>
          <select className={inp} value={form.assistant_id} onChange={set("assistant_id")} required>
            <option value="">— select assistant —</option>
            {assistants.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">Date & Time <span className="text-red-400">*</span></label>
          <input type="datetime-local" className={inp} value={form.scheduled_at} onChange={set("scheduled_at")} min={minDt} required />
        </div>
        {error && <p className="text-red-400 text-xs bg-red-900/30 border border-red-800 rounded p-2">{error}</p>}
        <div className="flex gap-3 pt-1">
          <button type="button" onClick={onClose} className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">Cancel</button>
          <button type="submit" disabled={loading} className="flex-1 py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium flex items-center justify-center gap-2">
            {loading ? <Spinner size={14} /> : <Calendar size={14} />}
            {loading ? "Scheduling…" : "Schedule Call"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ── Scheduled Calls Page ──────────────────────────────────────────────
export default function ScheduledCalls() {
  const [calls,       setCalls]       = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [showSchedule, setShowSchedule] = useState(false);
  const [now,         setNow]         = useState(Date.now());
  const { show, ToastEl } = useToast();

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try { setCalls(await api.calls.scheduled()); }
    catch (e) { show(e.message, "error"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function cancel(id) {
    try { await api.calls.cancelScheduled(id); show("Scheduled call cancelled"); load(); }
    catch (e) { show(e.message, "error"); }
  }

  return (
    <div className="space-y-6">
      {ToastEl}

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2"><Calendar size={22} /> Scheduled Calls</h1>
        <div className="flex items-center gap-2">
          <button onClick={load} className="p-2 text-gray-400 hover:text-white"><RefreshCw size={15} /></button>
          <button onClick={() => setShowSchedule(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium">
            <Plus size={14} /> Schedule Call
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : calls.length === 0 ? (
        <EmptyState icon={Calendar} title="No scheduled calls"
          description="Schedule a call to have it fire automatically at a specific time."
          action={<button onClick={() => setShowSchedule(true)} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium"><Plus size={14} /> Schedule Call</button>}
        />
      ) : (
        <div className="bg-gray-900 rounded overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-gray-800">
                <th className="text-left p-3">Lead</th>
                <th className="text-left p-3">Assistant</th>
                <th className="text-left p-3">Scheduled At</th>
                <th className="text-left p-3">Fires In</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {calls.map(sc => {
                const secLeft = Math.max(0, Math.round((new Date(sc.scheduled_at) - now) / 1000));
                return (
                  <tr key={sc.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                    <td className="p-3 font-medium">{sc.lead_name || `#${sc.lead_id}`}</td>
                    <td className="p-3 text-gray-300">{sc.assistant_name}</td>
                    <td className="p-3 text-gray-400 text-xs">{new Date(sc.scheduled_at).toLocaleString()}</td>
                    <td className="p-3">
                      <span className={`flex items-center gap-1 text-xs font-medium ${secLeft < 60 ? "text-yellow-400" : "text-blue-400"}`}>
                        <Clock size={12} /> {secondsToDisplay(secLeft)}
                      </span>
                    </td>
                    <td className="p-3">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-900 text-blue-200">{sc.status}</span>
                    </td>
                    <td className="p-3">
                      <button onClick={() => cancel(sc.id)}
                        className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-red-800 hover:bg-red-700 transition-colors">
                        <Trash2 size={11} /> Cancel
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {showSchedule && <ScheduleModal onClose={() => setShowSchedule(false)} onScheduled={() => { show("Call scheduled"); load(); }} />}
    </div>
  );
}
