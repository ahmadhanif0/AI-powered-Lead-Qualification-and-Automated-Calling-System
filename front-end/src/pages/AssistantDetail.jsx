import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Bot, Phone } from "lucide-react";
import { api }         from "../api/client";
import { useLeads }    from "../hooks/useLeads";
import { Spinner }     from "../components/Spinner";
import { Modal }       from "../components/Modal";
import { useToast }    from "../components/Toast";

// ── Start Call Modal (reused pattern) ───────────────────────────────
function CallModal({ assistant, leads, onClose, onSuccess }) {
  const [leadId,  setLeadId]  = useState("");
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const { startCall } = useLeads();

  async function handleCall() {
    if (!leadId) return;
    setLoading(true);
    setError(null);
    try {
      await startCall(parseInt(leadId));
      onSuccess("Call started successfully");
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Start Call">
      <div className="space-y-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Select Lead</label>
          <select
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            value={leadId}
            onChange={(e) => setLeadId(e.target.value)}
          >
            <option value="">— choose a lead —</option>
            {leads.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name || `Lead #${l.id}`} {l.phone ? `· ${l.phone}` : "(no phone)"}
              </option>
            ))}
          </select>
        </div>
        {error && <p className="text-red-400 text-xs bg-red-900/30 border border-red-800 rounded p-2">{error}</p>}
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm transition-colors">Cancel</button>
          <button onClick={handleCall} disabled={!leadId || loading}
            className="flex-1 py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium transition-colors flex items-center justify-center gap-2">
            {loading ? <Spinner size={14} /> : <Phone size={14} />}
            {loading ? "Calling…" : "Start Call"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ── Detail Row ───────────────────────────────────────────────────────
function Row({ label, value, mono = false }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start gap-1 py-3 border-b border-gray-800 last:border-0">
      <span className="text-gray-500 text-sm w-40 shrink-0">{label}</span>
      <span className={`text-sm text-gray-200 break-all ${mono ? "font-mono text-xs" : ""}`}>
        {value || <span className="text-gray-600">—</span>}
      </span>
    </div>
  );
}

// ── AssistantDetail Page ─────────────────────────────────────────────
export default function AssistantDetail() {
  const { id }       = useParams();
  const navigate     = useNavigate();
  const { leads }    = useLeads();
  const { show, ToastEl } = useToast();

  const [assistant, setAssistant] = useState(null);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState(null);
  const [showCall,  setShowCall]  = useState(false);

  useEffect(() => {
    api.assistants.get(id)
      .then(setAssistant)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="flex justify-center py-20"><Spinner /></div>;
  if (error)   return <div className="text-center text-red-400 py-12">{error}</div>;
  if (!assistant) return null;

  return (
    <div className="max-w-2xl space-y-6">
      {ToastEl}

      {/* Back + header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate("/assistants")}
          className="text-gray-400 hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </button>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-900 flex items-center justify-center">
            <Bot size={20} className="text-blue-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold">{assistant.name}</h1>
            <p className="text-xs text-gray-500">Assistant #{assistant.id}</p>
          </div>
        </div>
        <button
          onClick={() => setShowCall(true)}
          className="ml-auto flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium transition-colors"
        >
          <Phone size={14} /> Start Call
        </button>
      </div>

      {/* Details card */}
      <div className="bg-gray-900 rounded-xl p-5">
        <h2 className="font-semibold mb-2 text-sm text-gray-400 uppercase tracking-wide">Configuration</h2>
        <Row label="Name"           value={assistant.name} />
        <Row label="Voice"          value={assistant.voice_id} />
        <Row label="Model Provider" value={assistant.model_provider} />
        <Row label="Model"          value={assistant.model_name} />
        <Row label="VAPI ID"        value={assistant.vapi_assistant_id} mono />
      </div>

      {/* First message */}
      <div className="bg-gray-900 rounded-xl p-5">
        <h2 className="font-semibold mb-3 text-sm text-gray-400 uppercase tracking-wide">First Message</h2>
        <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
          {assistant.first_message || <span className="text-gray-600">Not set</span>}
        </p>
      </div>

      {/* System prompt */}
      <div className="bg-gray-900 rounded-xl p-5">
        <h2 className="font-semibold mb-3 text-sm text-gray-400 uppercase tracking-wide">System Prompt</h2>
        <pre className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap font-sans">
          {assistant.system_prompt || <span className="text-gray-600">Not set</span>}
        </pre>
      </div>

      {showCall && (
        <CallModal
          assistant={assistant}
          leads={leads}
          onClose={() => setShowCall(false)}
          onSuccess={(msg) => show(msg)}
        />
      )}
    </div>
  );
}
