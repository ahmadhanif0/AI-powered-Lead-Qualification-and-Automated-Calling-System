import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bot, Plus, Search, Phone, Eye, RefreshCw, Trash2, Pencil } from "lucide-react";
import { useAssistants }        from "../hooks/useAssistants";
import { useLeads }             from "../hooks/useLeads";
import { api }                  from "../api/client";
import { Spinner }              from "../components/Spinner";
import { EmptyState }           from "../components/EmptyState";
import { Modal }                from "../components/Modal";
import { DeleteConfirmModal }   from "../components/DeleteConfirmModal";
import { useToast }             from "../components/Toast";

// ── Shared constants ─────────────────────────────────────────────────
const VOICE_OPTIONS    = ["Elliot", "Lily", "Rohan", "Savannah", "Hana", "Cole"];
const MODEL_OPTIONS    = ["gpt-4.1", "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"];
const PROVIDER_OPTIONS = ["openai", "anthropic"];

const EMPTY_FORM = {
  name:           "",
  system_prompt:  "",
  first_message:  "",
  voice_id:       "Elliot",
  model_provider: "openai",
  model_name:     "gpt-4.1",
};

const inputCls = "w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors";
const labelCls = "block text-xs text-gray-400 mb-1";

// ── Shared assistant form (used by both Create and Edit modals) ───────
function AssistantForm({ form, setForm, onSubmit, onClose, loading, error, submitLabel }) {
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const valid = form.name.trim() && form.system_prompt.trim() && form.first_message.trim();

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className={labelCls}>Name <span className="text-red-400">*</span></label>
          <input className={inputCls} value={form.name} onChange={set("name")} placeholder="e.g. Sales Assistant" required />
        </div>

        <div className="col-span-2">
          <label className={labelCls}>First Message <span className="text-red-400">*</span></label>
          <input className={inputCls} value={form.first_message} onChange={set("first_message")}
            placeholder="Hi, I'm calling about your business growth…" required />
        </div>

        <div className="col-span-2">
          <label className={labelCls}>System Prompt <span className="text-red-400">*</span></label>
          <textarea className={`${inputCls} resize-none`} rows={5} value={form.system_prompt}
            onChange={set("system_prompt")}
            placeholder="You are a professional sales qualification agent. Your goal is to…" required />
        </div>

        <div>
          <label className={labelCls}>Voice</label>
          <select className={inputCls} value={form.voice_id} onChange={set("voice_id")}>
            {VOICE_OPTIONS.map((v) => <option key={v}>{v}</option>)}
          </select>
        </div>

        <div>
          <label className={labelCls}>Model Provider</label>
          <select className={inputCls} value={form.model_provider} onChange={set("model_provider")}>
            {PROVIDER_OPTIONS.map((p) => <option key={p}>{p}</option>)}
          </select>
        </div>

        <div className="col-span-2">
          <label className={labelCls}>Model</label>
          <select className={inputCls} value={form.model_name} onChange={set("model_name")}>
            {MODEL_OPTIONS.map((m) => <option key={m}>{m}</option>)}
          </select>
        </div>
      </div>

      {error && (
        <p className="text-red-400 text-xs bg-red-900/30 border border-red-800 rounded p-2">{error}</p>
      )}

      <div className="flex gap-3 pt-1">
        <button type="button" onClick={onClose}
          className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm transition-colors">
          Cancel
        </button>
        <button type="submit" disabled={loading || !valid}
          className="flex-1 py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium transition-colors flex items-center justify-center gap-2">
          {loading ? <Spinner size={14} /> : null}
          {loading ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}

// ── Create Assistant Modal ────────────────────────────────────────────
function CreateAssistantModal({ onClose, onCreate }) {
  const [form,    setForm]    = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true); setError(null);
    try { await onCreate(form); onClose(); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <Modal open onClose={onClose} title="Create Assistant" maxWidth="max-w-2xl">
      <AssistantForm form={form} setForm={setForm} onSubmit={handleSubmit}
        onClose={onClose} loading={loading} error={error} submitLabel="Create Assistant" />
    </Modal>
  );
}

// ── Edit Assistant Modal ──────────────────────────────────────────────
function EditAssistantModal({ assistant, onClose, onUpdated }) {
  const [form, setForm] = useState({
    name:           assistant.name           || "",
    system_prompt:  assistant.system_prompt  || "",
    first_message:  assistant.first_message  || "",
    voice_id:       assistant.voice_id       || "Elliot",
    model_provider: assistant.model_provider || "openai",
    model_name:     assistant.model_name     || "gpt-4.1",
  });
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      const updated = await api.assistants.update(assistant.id, form);
      onUpdated(updated);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={`Edit — ${assistant.name}`} maxWidth="max-w-2xl">
      <AssistantForm form={form} setForm={setForm} onSubmit={handleSubmit}
        onClose={onClose} loading={loading} error={error} submitLabel="Save Changes" />
    </Modal>
  );
}

// ── Start Call from Assistant ─────────────────────────────────────────
function CallFromAssistantModal({ assistant, leads, onClose, onSuccess }) {
  const [leadId,  setLeadId]  = useState("");
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const { startCall } = useLeads();

  async function handleCall() {
    if (!leadId) return;
    setLoading(true); setError(null);
    try {
      await startCall(parseInt(leadId));
      onSuccess(`Call started via ${assistant.name}`);
      onClose();
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <Modal open onClose={onClose} title={`Start Call — ${assistant.name}`}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Select Lead</label>
          <select className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            value={leadId} onChange={(e) => setLeadId(e.target.value)}>
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

// ── Assistants Page ───────────────────────────────────────────────────
export default function Assistants() {
  const navigate = useNavigate();
  const { assistants, loading, error, reload, create } = useAssistants();
  const { leads }    = useLeads();
  const { show, ToastEl } = useToast();

  const [search,      setSearch]      = useState("");
  const [showCreate,  setShowCreate]  = useState(false);
  const [editTarget,  setEditTarget]  = useState(null);   // assistant being edited
  const [callTarget,  setCallTarget]  = useState(null);   // assistant for call modal
  const [deleteModal, setDeleteModal] = useState({ open: false, assistant: null });
  const [deletingId,  setDeletingId]  = useState(null);

  const filtered = assistants.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase())
  );

  // ── Handlers ─────────────────────────────────────────────────────

  async function handleCreate(payload) {
    await create(payload);
    show("Assistant created successfully");
  }

  function handleUpdated(updated) {
    // Optimistically update the list without a full reload
    reload();
    show(`"${updated.name}" updated in database and VAPI`);
  }

  function openDeleteModal(a) {
    setDeleteModal({ open: true, assistant: a });
  }

  async function handleDeleteConfirm() {
    const a = deleteModal.assistant;
    setDeletingId(a.id);
    try {
      await api.assistants.delete(a.id);
      show(`"${a.name}" deleted from database and VAPI`);
      setDeleteModal({ open: false, assistant: null });
      reload();
    } catch (e) {
      show(e.message, "error");
    } finally {
      setDeletingId(null);
    }
  }

  // ── Render ────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {ToastEl}

      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Assistants</h1>
        <div className="flex items-center gap-3">
          <button onClick={reload}
            className="flex items-center gap-1 text-gray-400 hover:text-white text-sm transition-colors">
            <RefreshCw size={14} />
          </button>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium transition-colors">
            <Plus size={15} /> New Assistant
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          className="w-full pl-8 py-2 pr-3 bg-gray-800 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-600"
          placeholder="Search assistants…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : error ? (
        <div className="text-center text-red-400 py-12 text-sm">{error}</div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="No assistants yet"
          description="Create your first AI assistant to start making calls."
          action={
            <button onClick={() => setShowCreate(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium transition-colors">
              <Plus size={14} /> Create Assistant
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((a) => (
            <div key={a.id}
              className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3 hover:border-gray-700 transition-colors">

              {/* Card header */}
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-blue-900 flex items-center justify-center">
                    <Bot size={18} className="text-blue-400" />
                  </div>
                  <div>
                    <div className="font-semibold text-sm">{a.name}</div>
                    <div className="text-xs text-gray-500">{a.model_name}</div>
                  </div>
                </div>
              </div>

              {/* Meta */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-gray-800 rounded p-2">
                  <div className="text-gray-500 mb-0.5">Voice</div>
                  <div className="text-gray-200">{a.voice_id}</div>
                </div>
                <div className="bg-gray-800 rounded p-2">
                  <div className="text-gray-500 mb-0.5">Provider</div>
                  <div className="text-gray-200 capitalize">{a.model_provider || "openai"}</div>
                </div>
              </div>

              {/* VAPI ID */}
              {a.vapi_assistant_id && (
                <div className="text-xs text-gray-600 truncate" title={a.vapi_assistant_id}>
                  VAPI: {a.vapi_assistant_id}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-1">
                <button onClick={() => navigate(`/assistants/${a.id}`)}
                  className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded bg-gray-700 hover:bg-gray-600 text-xs transition-colors">
                  <Eye size={12} /> Details
                </button>
                <button onClick={() => setEditTarget(a)}
                  className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded bg-gray-700 hover:bg-gray-600 text-xs transition-colors">
                  <Pencil size={12} /> Edit
                </button>
                <button onClick={() => setCallTarget(a)}
                  className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded bg-blue-700 hover:bg-blue-600 text-xs transition-colors">
                  <Phone size={12} /> Call
                </button>
                <button
                  onClick={() => openDeleteModal(a)}
                  disabled={deletingId === a.id}
                  title="Delete assistant (also removes from VAPI)"
                  className="flex items-center justify-center px-2 py-1.5 rounded bg-red-800 hover:bg-red-700 disabled:opacity-50 text-xs transition-colors"
                >
                  {deletingId === a.id ? <Spinner size={11} /> : <Trash2 size={12} />}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Modals ── */}

      {showCreate && (
        <CreateAssistantModal
          onClose={() => setShowCreate(false)}
          onCreate={handleCreate}
        />
      )}

      {editTarget && (
        <EditAssistantModal
          assistant={editTarget}
          onClose={() => setEditTarget(null)}
          onUpdated={handleUpdated}
        />
      )}

      {callTarget && (
        <CallFromAssistantModal
          assistant={callTarget}
          leads={leads}
          onClose={() => setCallTarget(null)}
          onSuccess={(msg) => show(msg)}
        />
      )}

      <DeleteConfirmModal
        open={deleteModal.open}
        onClose={() => !deletingId && setDeleteModal({ open: false, assistant: null })}
        onConfirm={handleDeleteConfirm}
        title="Delete Assistant"
        itemName={deleteModal.assistant?.name}
        warning="This will permanently delete the assistant from both the local database and VAPI. Any active calls using this assistant may be affected."
        isDeleting={deletingId === deleteModal.assistant?.id}
      />
    </div>
  );
}
