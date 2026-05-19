import { useState, useCallback, useEffect, useRef } from "react";
import { Users, Upload, Download, Search, Filter, Phone, X,
         RefreshCw, CheckCircle, Eye, Pencil, Trash2, Plus, FileText } from "lucide-react";
import { useAuth }             from "../context/AuthContext";
import { api }                 from "../api/client";
import { Spinner }             from "../components/Spinner";
import { Modal }               from "../components/Modal";
import { DeleteConfirmModal }  from "../components/DeleteConfirmModal";
import { Pagination }          from "../components/Pagination";
import { useToast }            from "../components/Toast";
import { LiveTranscriptModal } from "../components/LiveTranscriptModal";
import { leadStatusColor, callStatusColor, callStatusLabel, decisionColor }
  from "../lib/helpers";

const STATUS_OPTIONS = ["", "Booked", "Rejected", "Pending", "Won't Follow Up"];
const STAGE_OPTIONS  = ["", "lead", "subscriber", "marketingqualifiedlead",
                        "salesqualifiedlead", "opportunity"];
const SORT_OPTIONS   = [
  { value: "updated_at",   label: "Last Updated" },
  { value: "score",        label: "Score" },
  { value: "created_at",  label: "Date Created" },
  { value: "last_call_at", label: "Last Call" },
];
const PAGE_SIZE = 10;

// ── Score badge ───────────────────────────────────────────────────────
function ScoreBadge({ score }) {
  const s = Math.round(score ?? 0);
  const cls = s >= 70 ? "text-green-400" : s >= 40 ? "text-yellow-400" : "text-red-400";
  return <span className={`font-bold ${cls}`}>{s}</span>;
}

// ── View Lead Modal ───────────────────────────────────────────────────
function ViewLeadModal({ lead, onClose, onEdit }) {
  const rows = [
    ["First Name",  lead.first_name],
    ["Last Name",   lead.last_name],
    ["Email",       lead.email],
    ["Phone",       lead.phone],
    ["Company",     lead.company],
    ["Stage",       lead.lead_stage],
    ["Status",      lead.status],
    ["Call Status", lead.call_status],
    ["AI Decision", lead.ai_decision],
    ["Retries",     lead.retry_count],
    ["HubSpot ID",  lead.hubspot_id],
    ["Created",     lead.created_at ? new Date(lead.created_at).toLocaleString() : null],
    ["Updated",     lead.updated_at ? new Date(lead.updated_at).toLocaleString() : null],
  ];

  return (
    <Modal open onClose={onClose} title={lead.name || `Lead #${lead.id}`} maxWidth="max-w-lg">
      <div className="space-y-3">
        <div className="flex items-center gap-3 pb-2 border-b border-gray-800">
          <div>
            <div className="text-xs text-gray-500">Score</div>
            <ScoreBadge score={lead.score} />
          </div>
        </div>
        <div className="space-y-1">
          {rows.map(([label, value]) => value != null && value !== "" && (
            <div key={label} className="flex gap-3 text-sm py-1 border-b border-gray-800/50">
              <span className="text-gray-500 w-28 shrink-0">{label}</span>
              <span className="text-gray-200 break-all">{String(value)}</span>
            </div>
          ))}
        </div>
        {lead.last_transcript && (
          <div>
            <div className="text-xs text-gray-500 mb-1">Last Transcript</div>
            <pre className="text-xs text-gray-300 bg-gray-800 rounded p-2 max-h-32 overflow-y-auto whitespace-pre-wrap">
              {lead.last_transcript}
            </pre>
          </div>
        )}
        <div className="flex gap-3 pt-1">
          <button onClick={onClose}
            className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">Close</button>
          <button onClick={() => { onClose(); onEdit(lead); }}
            className="flex-1 py-2 rounded bg-blue-600 hover:bg-blue-500 text-sm font-medium flex items-center justify-center gap-2">
            <Pencil size={13} /> Edit
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ── Badge helpers ─────────────────────────────────────────────────────
function stageBadgeCls(stage) {
  return {
    new:           "bg-gray-700 text-gray-300",
    contacted:     "bg-blue-900 text-blue-300",
    qualified:     "bg-green-900 text-green-300",
    interested:    "bg-green-800 text-green-200",
    not_interested:"bg-red-900 text-red-300",
    call_later:    "bg-yellow-900 text-yellow-300",
    wrong_number:  "bg-gray-700 text-gray-400",
  }[stage?.toLowerCase()] || "bg-gray-700 text-gray-300";
}

function statusBadgeCls(status) {
  return {
    "Pending":          "bg-yellow-900 text-yellow-300",
    "Booked":           "bg-green-900 text-green-300",
    "Rejected":         "bg-red-900 text-red-300",
    "Won't Follow Up":  "bg-gray-700 text-gray-400",
  }[status] || "bg-gray-700 text-gray-300";
}

function aiDecisionBadgeCls(decision) {
  return {
    "Interested":     "bg-green-900 text-green-300",
    "Not Interested": "bg-red-900 text-red-300",
    "Call Later":     "bg-blue-900 text-blue-300",
    "Wrong Number":   "bg-gray-700 text-gray-400",
    "No Response":    "bg-orange-900 text-orange-300",
  }[decision] || "bg-gray-700 text-gray-300";
}

// ── Edit Lead Modal ───────────────────────────────────────────────────
function EditLeadModal({ lead, onClose, onSaved, isAdmin = false }) {
  // Contact-info fields + optional manual status override
  const [form, setForm] = useState({
    first_name: lead.first_name || "",
    last_name:  lead.last_name  || "",
    email:      lead.email      || "",
    phone:      lead.phone      || "",
    company:    lead.company    || "",
    status:     lead.status     || "",
  });
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  async function handleSave(ev) {
    ev.preventDefault();
    setLoading(true); setError(null);
    try {
      const fn = isAdmin ? api.admin.leads.update : api.leads.update;
      const updated = await fn(lead.id, {
        first_name: form.first_name,
        last_name:  form.last_name  || undefined,
        email:      form.email,
        phone:      form.phone      || undefined,
        company:    form.company    || undefined,
        status:     form.status     || undefined,
      });
      onSaved(updated);   // pass updated lead back so table row refreshes immediately
      onClose();
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  const inp = "w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500";
  const lbl = "block text-xs text-gray-400 mb-1";

  return (
    <Modal open onClose={onClose} title={`Edit — ${lead.name || `Lead #${lead.id}`}`} maxWidth="max-w-lg">
      <form onSubmit={handleSave} className="space-y-4">

        {/* System-controlled fields — read-only display */}
        <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-3 space-y-2">
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
            System-controlled (auto-updated by AI)
          </p>
          <div className="flex flex-wrap gap-3 text-xs">
            {lead.ai_decision && (
              <div>
                <span className="text-gray-500 mr-1">AI Decision:</span>
                <span className={`px-2 py-0.5 rounded-full font-medium ${aiDecisionBadgeCls(lead.ai_decision)}`}>
                  {lead.ai_decision}
                </span>
              </div>
            )}
            {lead.lead_stage && (
              <div>
                <span className="text-gray-500 mr-1">Stage:</span>
                <span className={`px-2 py-0.5 rounded-full font-medium capitalize ${stageBadgeCls(lead.lead_stage)}`}>
                  {lead.lead_stage}
                </span>
              </div>
            )}
            {lead.status && (
              <div>
                <span className="text-gray-500 mr-1">Status:</span>
                <span className={`px-2 py-0.5 rounded-full font-medium ${statusBadgeCls(lead.status)}`}>
                  {lead.status}
                </span>
              </div>
            )}
          </div>
          <p className="text-xs text-gray-600">
            Stage and status are set automatically by AI call outcomes and workflow actions.
          </p>
        </div>

        {/* Editable contact-info fields */}
        <div className="grid grid-cols-2 gap-3">
          <div><label className={lbl}>First Name</label>
            <input className={inp} value={form.first_name} onChange={set("first_name")} /></div>
          <div><label className={lbl}>Last Name</label>
            <input className={inp} value={form.last_name}  onChange={set("last_name")} /></div>
          <div className="col-span-2"><label className={lbl}>Email</label>
            <input type="email" className={inp} value={form.email} onChange={set("email")} /></div>
          <div><label className={lbl}>Phone</label>
            <input className={inp} value={form.phone}   onChange={set("phone")} /></div>
          <div><label className={lbl}>Company</label>
            <input className={inp} value={form.company} onChange={set("company")} /></div>
          <div className="col-span-2">
            <label className={lbl}>
              Status <span className="text-gray-600 font-normal">(manual override)</span>
            </label>
            <select className={inp} value={form.status} onChange={set("status")}>
              <option value="">— keep current ({lead.status || "Pending"}) —</option>
              <option value="Pending">Pending</option>
              <option value="Booked">Booked</option>
              <option value="Rejected">Rejected</option>
              <option value="Won't Follow Up">Won't Follow Up</option>
            </select>
          </div>
        </div>

        {error && <p className="text-red-400 text-xs bg-red-900/30 border border-red-800 rounded p-2">{error}</p>}
        <div className="flex gap-3">
          <button type="button" onClick={onClose}
            className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">Cancel</button>
          <button type="submit" disabled={loading}
            className="flex-1 py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium flex items-center justify-center gap-2">
            {loading ? <Spinner size={14} /> : null}
            {loading ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ── Create Lead Modal ─────────────────────────────────────────────────
function CreateLeadModal({ onClose, onCreated, isAdmin = false, users = [] }) {
  const [form, setForm] = useState({
    first_name:        "",
    last_name:         "",
    email:             "",
    phone:             "",
    company:           "",
    assign_to_user_id: "",
  });
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const [result,  setResult]  = useState(null);
  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  // Live stage detection — mirrors backend infer_stage() logic exactly
  const autoStage = (() => {
    const { email, phone, company } = form;
    if (email && phone && company) return "qualified";
    if (email && phone)            return "contacted";
    return "new";
  })();

  const stageLabel = { new: "New", contacted: "Contacted", qualified: "Qualified" }[autoStage] || autoStage;
  const stageReason = {
    qualified: "Has email + phone + company",
    contacted: "Has email + phone",
    new:       "Email only",
  }[autoStage];

  async function handleSubmit(ev) {
    ev.preventDefault();
    setLoading(true); setError(null);
    try {
      // Stage is NOT sent — backend always uses infer_stage()
      const payload = {
        first_name: form.first_name,
        last_name:  form.last_name  || undefined,
        email:      form.email,
        phone:      form.phone      || undefined,
        company:    form.company    || undefined,
      };
      if (isAdmin && form.assign_to_user_id) {
        payload.assign_to_user_id = parseInt(form.assign_to_user_id);
      }
      const r = await api.leads.create(payload);
      setResult(r);
      onCreated();
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  const inp = "w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500";
  const lbl = "block text-xs text-gray-400 mb-1";

  if (result) {
    return (
      <Modal open onClose={onClose} title="Lead Created">
        <div className="space-y-4">
          <div className="bg-green-900/20 border border-green-800 rounded-lg p-4 space-y-2 text-sm">
            <div className="flex items-center gap-2 text-green-400 font-medium">
              <CheckCircle size={16} /> Lead created successfully
            </div>
            <div className="text-gray-300">Name: <span className="text-white">{result.first_name} {result.last_name || ""}</span></div>
            <div className="text-gray-300">Email: <span className="text-white">{result.email}</span></div>
            <div className="text-gray-300">Score: <ScoreBadge score={result.score} /></div>
            <div className="flex items-center gap-2 text-gray-300">
              Stage:
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${stageBadgeCls(result.lead_stage)}`}>
                {result.lead_stage}
              </span>
              <span className="text-gray-600 text-xs">(auto-detected)</span>
            </div>
          </div>

          {/* HubSpot push result */}
          {result.hubspot_pushed ? (
            <div className="flex items-center gap-2 text-orange-400 text-xs bg-orange-900/20 border border-orange-800 rounded p-2">
              <CheckCircle size={12} /> Also saved to HubSpot
            </div>
          ) : result.hubspot_error ? (
            <div className="text-xs bg-yellow-900/20 border border-yellow-700 rounded p-3 space-y-1">
              <div className="flex items-center gap-1 text-yellow-400 font-medium">
                ⚠ HubSpot push failed — lead saved locally
              </div>
              <div className="text-gray-400 break-all">{result.hubspot_error}</div>
              <div className="text-gray-600">
                {result.hubspot_error.toLowerCase().includes("not connected")
                  ? "Connect HubSpot in Settings to sync leads automatically."
                  : "Check your HubSpot connection in Settings and try syncing manually."}
              </div>
            </div>
          ) : null}

          <button onClick={onClose}
            className="w-full py-2 rounded bg-blue-600 hover:bg-blue-500 text-sm font-medium">
            Done
          </button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal open onClose={onClose} title="Create Lead" maxWidth="max-w-lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div><label className={lbl}>First Name <span className="text-red-400">*</span></label>
            <input className={inp} value={form.first_name} onChange={set("first_name")} required /></div>
          <div><label className={lbl}>Last Name</label>
            <input className={inp} value={form.last_name}  onChange={set("last_name")} /></div>
          <div className="col-span-2"><label className={lbl}>Email <span className="text-red-400">*</span></label>
            <input type="email" className={inp} value={form.email} onChange={set("email")} required /></div>
          <div><label className={lbl}>Phone</label>
            <input className={inp} value={form.phone}   onChange={set("phone")} placeholder="+1234567890" /></div>
          <div><label className={lbl}>Company</label>
            <input className={inp} value={form.company} onChange={set("company")} /></div>
        </div>

        {/* Auto-detected stage preview — read-only, updates live */}
        <div className="bg-gray-800/60 border border-gray-700 rounded-lg p-3 space-y-1">
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
            Stage (Auto-detected)
          </p>
          <div className="flex items-center justify-between">
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${stageBadgeCls(autoStage)}`}>
              {stageLabel}
            </span>
            <span className="text-xs text-gray-600">{stageReason}</span>
          </div>
          <p className="text-xs text-gray-600">
            Stage is determined automatically. Add phone and company to qualify the lead.
          </p>
        </div>

        {isAdmin && users.length > 0 && (
          <div><label className={lbl}>Assign to User</label>
            <select className={inp} value={form.assign_to_user_id} onChange={set("assign_to_user_id")}>
              <option value="">— myself (admin) —</option>
              {users.map(u => (
                <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
              ))}
            </select></div>
        )}

        {error && <p className="text-red-400 text-xs bg-red-900/30 border border-red-800 rounded p-2">{error}</p>}
        <div className="flex gap-3">
          <button type="button" onClick={onClose}
            className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">Cancel</button>
          <button type="submit" disabled={loading}
            className="flex-1 py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium flex items-center justify-center gap-2">
            {loading ? <Spinner size={14} /> : <Plus size={14} />}
            {loading ? "Creating…" : "Create Lead"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
function CsvImportModal({ onClose, onImported }) {
  const [file,    setFile]    = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result,  setResult]  = useState(null);
  const [error,   setError]   = useState(null);
  const fileRef = useRef();

  function handleFile(f) {
    if (!f) return;
    setFile(f); setResult(null); setError(null);
    const reader = new FileReader();
    reader.onload = (e) => {
      const lines = e.target.result.split("\n").slice(0, 6).filter(Boolean);
      setPreview(lines.map(l => l.split(",")));
    };
    reader.readAsText(f);
  }

  async function handleUpload() {
    if (!file) return;
    setLoading(true); setError(null);
    try { const r = await api.leads.uploadCsv(file); setResult(r); onImported(); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  return (
    <Modal open onClose={onClose} title="Import CSV" maxWidth="max-w-2xl">
      <div className="space-y-4">
        <a href={api.leads.downloadTemplate()} download="leads_template.csv"
          className="flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300">
          <Download size={13} /> Download template
          <span className="text-gray-600">(first_name, last_name, email, phone, company, lead_stage)</span>
        </a>
        <div onClick={() => fileRef.current?.click()}
          className="border-2 border-dashed border-gray-700 rounded-lg p-6 text-center cursor-pointer hover:border-blue-600 transition-colors">
          <Upload size={24} className="mx-auto text-gray-500 mb-2" />
          <p className="text-sm text-gray-400">{file ? file.name : "Click to select a .csv file"}</p>
          <p className="text-xs text-gray-600 mt-1">Max 1,000 rows · 5 MB</p>
          <input ref={fileRef} type="file" accept=".csv" className="hidden"
            onChange={e => handleFile(e.target.files[0])} />
        </div>
        {preview && (
          <div className="overflow-x-auto rounded border border-gray-800">
            <table className="w-full text-xs">
              <thead><tr className="bg-gray-800">
                {preview[0]?.map((h, i) => <th key={i} className="p-2 text-left text-gray-400">{h}</th>)}
              </tr></thead>
              <tbody>{preview.slice(1).map((row, i) => (
                <tr key={i} className="border-t border-gray-800">
                  {row.map((cell, j) => <td key={j} className="p-2 text-gray-300">{cell}</td>)}
                </tr>
              ))}</tbody>
            </table>
            <p className="text-xs text-gray-600 p-2">First 5 rows</p>
          </div>
        )}
        {result && (
          <div className="bg-green-900/20 border border-green-800 rounded-lg p-3 text-sm space-y-1">
            <div className="flex items-center gap-2 text-green-400 font-medium"><CheckCircle size={14} /> Import complete</div>
            <div className="text-gray-300">Saved: <span className="text-green-400 font-bold">{result.imported}</span></div>
            {result.hubspot_pushed > 0 && <div className="text-gray-300">HubSpot: <span className="text-orange-400 font-bold">{result.hubspot_pushed}</span></div>}
            <div className="text-gray-300">Skipped: <span className="text-yellow-400">{result.skipped}</span></div>
            {result.errors?.length > 0 && (
              <div className="text-red-400 text-xs">Errors: {result.errors.length}
                <ul className="mt-1">{result.errors.slice(0,5).map((e,i) => <li key={i}>Row {e.row}: {e.reason}</li>)}</ul>
              </div>
            )}
          </div>
        )}
        {error && <p className="text-red-400 text-xs bg-red-900/30 border border-red-800 rounded p-2">{error}</p>}
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">
            {result ? "Close" : "Cancel"}
          </button>
          {!result && (
            <button onClick={handleUpload} disabled={!file || loading}
              className="flex-1 py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium flex items-center justify-center gap-2">
              {loading ? <Spinner size={14} /> : <Upload size={14} />}
              {loading ? "Importing…" : "Import"}
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}

// ── Leads Page ────────────────────────────────────────────────────────
export default function Leads() {
  const { isAdmin, loading: authLoading } = useAuth();
  const { show, ToastEl } = useToast();
  const [leads,       setLeads]       = useState([]);
  const [total,       setTotal]       = useState(0);
  const [loading,     setLoading]     = useState(true);
  const [page,        setPage]        = useState(1);
  const [showImport,  setShowImport]  = useState(false);
  const [showCreate,  setShowCreate]  = useState(false);
  const [viewLead,    setViewLead]    = useState(null);
  const [editLead,    setEditLead]    = useState(null);
  const [deleteLead,  setDeleteLead]  = useState(null);
  const [deleting,    setDeleting]    = useState(false);
  const [callLead,    setCallLead]    = useState(null);
  const [transcriptLead, setTranscriptLead] = useState(null);  // LiveTranscriptModal

  // Admin user filter
  const [users,          setUsers]          = useState([]);
  const [filterUserId,   setFilterUserId]   = useState("");

  // Filters
  const [search,      setSearch]      = useState("");
  const [status,      setStatus]      = useState("");
  const [stage,       setStage]       = useState("");
  const [scoreMin,    setScoreMin]    = useState("");
  const [scoreMax,    setScoreMax]    = useState("");
  const [sort,        setSort]        = useState("updated_at");
  const [order,       setOrder]       = useState("desc");
  const [showFilters, setShowFilters] = useState(false);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Load admin user list for filter dropdown
  useEffect(() => {
    if (!isAdmin) return;
    api.admin.users.list({ page_size: 100 })
      .then(d => setUsers(d.users || []))
      .catch(console.error);
  }, [isAdmin]);

  const load = useCallback(async (p = 1) => {
    // Don't fetch until auth has finished verifying the token
    if (authLoading) return;
    setLoading(true);
    try {
      const params = { page: p, page_size: PAGE_SIZE, sort, order };
      if (search)       params.search     = search;
      if (status)       params.status     = status;
      if (stage)        params.lead_stage = stage;
      if (scoreMin)     params.score_min  = scoreMin;
      if (scoreMax)     params.score_max  = scoreMax;
      if (isAdmin && filterUserId) params.user_id = filterUserId;

      const fn   = isAdmin ? api.admin.leads.list : api.leads.list;
      const data = await fn(params);
      setLeads(data.leads || []);
      setTotal(data.total || 0);
      setPage(p);
    } catch (e) { show(e.message, "error"); }
    finally { setLoading(false); }
  }, [authLoading, search, status, stage, scoreMin, scoreMax, sort, order, isAdmin, filterUserId]);

  // Re-run when auth finishes loading (authLoading goes false → true → false)
  useEffect(() => {
    if (!authLoading) load(1);
  }, [authLoading, load]);

  function clearFilters() {
    setSearch(""); setStatus(""); setStage("");
    setScoreMin(""); setScoreMax("");
    setSort("updated_at"); setOrder("desc");
    setFilterUserId("");
  }

  async function handleDelete() {
    if (!deleteLead) return;
    setDeleting(true);
    try {
      const fn = isAdmin ? api.admin.leads.delete : api.leads.delete;
      await fn(deleteLead.id);
      show(`"${deleteLead.name || `Lead #${deleteLead.id}`}" deleted`);
      setDeleteLead(null);
      load(page);
    } catch (e) { show(e.message, "error"); }
    finally { setDeleting(false); }
  }

  const hasFilters = search || status || stage || scoreMin || scoreMax || filterUserId;
  const selCls = "bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs focus:outline-none focus:border-blue-500";

  return (
    <div className="space-y-4">
      {ToastEl}

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Users size={22} /> Leads
          <span className="text-sm text-gray-500 font-normal">({total})</span>
        </h1>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={() => load(page)} className="p-2 text-gray-400 hover:text-white"><RefreshCw size={15} /></button>
          <button onClick={() => setShowFilters(v => !v)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded text-xs transition-colors ${showFilters || hasFilters ? "bg-blue-700 text-white" : "bg-gray-800 text-gray-400 hover:text-white"}`}>
            <Filter size={13} /> Filters {hasFilters && "•"}
          </button>
          <button onClick={() => setShowImport(true)}
            className="flex items-center gap-1 px-3 py-1.5 rounded bg-green-700 hover:bg-green-600 text-xs font-medium">
            <Upload size={13} /> Import CSV
          </button>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-1 px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-xs font-medium">
            <Plus size={13} /> Create Lead
          </button>
        </div>
      </div>

      {/* Search + sort */}
      <div className="flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input className="w-full pl-8 py-2 pr-3 bg-gray-800 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-600"
            placeholder="Search name, email, company…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        {isAdmin && (
          <select className={selCls} value={filterUserId} onChange={e => setFilterUserId(e.target.value)}>
            <option value="">All Users</option>
            {users.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>)}
          </select>
        )}
        <select className={selCls} value={sort} onChange={e => setSort(e.target.value)}>
          {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select className={selCls} value={order} onChange={e => setOrder(e.target.value)}>
          <option value="desc">↓ Desc</option>
          <option value="asc">↑ Asc</option>
        </select>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div><label className="text-xs text-gray-500 block mb-1">Status</label>
            <select className={`${selCls} w-full`} value={status} onChange={e => setStatus(e.target.value)}>
              {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s || "All"}</option>)}
            </select></div>
          <div><label className="text-xs text-gray-500 block mb-1">Stage</label>
            <select className={`${selCls} w-full`} value={stage} onChange={e => setStage(e.target.value)}>
              {STAGE_OPTIONS.map(s => <option key={s} value={s}>{s || "All"}</option>)}
            </select></div>
          <div><label className="text-xs text-gray-500 block mb-1">Min Score</label>
            <input type="number" min={0} max={100} className={`${selCls} w-full`} value={scoreMin} onChange={e => setScoreMin(e.target.value)} placeholder="0" /></div>
          <div><label className="text-xs text-gray-500 block mb-1">Max Score</label>
            <input type="number" min={0} max={100} className={`${selCls} w-full`} value={scoreMax} onChange={e => setScoreMax(e.target.value)} placeholder="100" /></div>
          <div className="col-span-2 sm:col-span-4 flex justify-end">
            <button onClick={clearFilters} className="flex items-center gap-1 text-xs text-gray-400 hover:text-white">
              <X size={12} /> Clear filters
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-gray-900 rounded overflow-x-auto">
        {loading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : leads.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">No leads found</div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b border-gray-800">
                  <th className="text-left p-3">Name</th>
                  {isAdmin && <th className="text-left p-3">Owner</th>}
                  <th className="text-left p-3">Company</th>
                  <th className="text-left p-3">Email</th>
                  <th className="text-left p-3">Score</th>
                  <th className="text-left p-3">Stage</th>
                  <th className="text-left p-3">Status</th>
                  <th className="text-left p-3">Call</th>
                  <th className="text-left p-3">Decision</th>
                  <th className="text-left p-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {leads.map(l => (
                  <tr key={l.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                    <td className="p-3">
                      <div className="font-medium">{l.name || "—"}</div>
                      <div className="text-xs text-gray-500">{l.phone || ""}</div>
                    </td>
                    {isAdmin && (
                      <td className="p-3 text-xs text-gray-500">{l.owner_email || `#${l.user_id}`}</td>
                    )}
                    <td className="p-3 text-gray-300 text-xs">{l.company || "—"}</td>
                    <td className="p-3 text-gray-400 text-xs">{l.email || "—"}</td>
                    <td className="p-3"><ScoreBadge score={l.score} /></td>
                    <td className="p-3 text-gray-400 text-xs capitalize">{l.stage || "—"}</td>
                    <td className={`p-3 text-xs font-semibold ${leadStatusColor(l.status)}`}>{l.status || "—"}</td>
                    <td className={`p-3 text-xs ${callStatusColor(l.call_status)}`}>{callStatusLabel(l.call_status)}</td>
                    <td className={`p-3 text-xs ${decisionColor(l.ai_decision)}`}>{l.ai_decision || "—"}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-1">
                        <button onClick={() => setViewLead(l)} title="View"
                          className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors">
                          <Eye size={13} />
                        </button>
                        <button onClick={() => setEditLead(l)} title="Edit"
                          className="p-1.5 rounded hover:bg-gray-700 text-blue-400 hover:text-blue-300 transition-colors">
                          <Pencil size={13} />
                        </button>
                        <button onClick={() => setCallLead(l)} title="Call"
                          className="p-1.5 rounded hover:bg-gray-700 text-green-400 hover:text-green-300 transition-colors">
                          <Phone size={13} />
                        </button>
                        {/* Live — shown while call is active */}
                        {["calling", "in-progress", "in_progress", "queued"].includes(l.call_status) && (
                          <button onClick={() => setTranscriptLead(l)} title="Live transcript"
                            className="p-1.5 rounded hover:bg-gray-700 text-red-400 hover:text-red-300 transition-colors animate-pulse">
                            <FileText size={13} />
                          </button>
                        )}
                        {/* Recording — shown when call completed */}
                        {l.call_status === "completed" && (
                          <button onClick={() => setTranscriptLead(l)} title="View transcript & recording"
                            className="p-1.5 rounded hover:bg-gray-700 text-yellow-400 hover:text-yellow-300 transition-colors">
                            <Download size={13} />
                          </button>
                        )}
                        <button onClick={() => setDeleteLead(l)} title="Delete"
                          className="p-1.5 rounded hover:bg-gray-700 text-red-400 hover:text-red-300 transition-colors">
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <Pagination
              currentPage={page}
              totalPages={totalPages}
              total={total}
              pageSize={PAGE_SIZE}
              onPageChange={(p) => load(p)}
            />
          </>
        )}
      </div>

      {/* ── Modals ── */}

      {/* View */}
      {viewLead && (
        <ViewLeadModal
          lead={viewLead}
          onClose={() => setViewLead(null)}
          onEdit={(l) => setEditLead(l)}
        />
      )}

      {/* Edit */}
      {editLead && (
        <EditLeadModal
          lead={editLead}
          isAdmin={isAdmin}
          onClose={() => setEditLead(null)}
          onSaved={(updated) => {
            show("Lead updated successfully");
            if (updated) {
              // Merge updated fields into the existing row immediately
              setLeads(prev => prev.map(l =>
                l.id === updated.id
                  ? {
                      ...l,
                      first_name:  updated.first_name,
                      last_name:   updated.last_name,
                      name:        `${updated.first_name || ""} ${updated.last_name || ""}`.trim(),
                      email:       updated.email,
                      phone:       updated.phone,
                      company:     updated.company,
                      status:      updated.status,
                      score:       updated.score,
                      lead_stage:  updated.lead_stage,
                      stage:       updated.lead_stage,
                      ai_decision: updated.ai_decision,
                      updated_at:  updated.updated_at,
                    }
                  : l
              ));
            } else {
              load(page);
            }
          }}
        />
      )}

      {/* Delete confirmation */}
      <DeleteConfirmModal
        open={!!deleteLead}
        onClose={() => !deleting && setDeleteLead(null)}
        onConfirm={handleDelete}
        title="Delete Lead?"
        itemName={deleteLead?.name || (deleteLead ? `Lead #${deleteLead.id}` : "")}
        warning="This will permanently remove the lead from the database. If connected to HubSpot, the contact will also be archived there."
        isDeleting={deleting}
      />

      {/* Start Call */}
      {callLead && (
        <Modal open onClose={() => setCallLead(null)} title="Start AI Call">
          <div className="space-y-4">
            <div className="bg-gray-800 rounded-lg p-4 space-y-1 text-sm">
              {[
                ["Lead",    callLead.name    || `#${callLead.id}`],
                ["Phone",   callLead.phone   || "—"],
                ["Company", callLead.company || "—"],
                ["Score",   Math.round(callLead.score ?? 0)],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-gray-400">{k}</span>
                  <span>{v}</span>
                </div>
              ))}
            </div>
            {!callLead.phone && (
              <p className="text-yellow-400 text-xs bg-yellow-900/30 border border-yellow-800 rounded p-2">
                ⚠ No phone number — the call may fail.
              </p>
            )}
            <div className="flex gap-3">
              <button onClick={() => setCallLead(null)}
                className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">Cancel</button>
              <button
                onClick={async () => {
                  try {
                    await api.calls.start(callLead.id);
                    show(`Call started for ${callLead.name || `Lead #${callLead.id}`}`);
                    setCallLead(null);
                    load(page);
                  } catch (e) { show(e.message, "error"); }
                }}
                className="flex-1 py-2 rounded bg-blue-600 hover:bg-blue-500 text-sm font-medium flex items-center justify-center gap-2">
                <Phone size={14} /> Start Call
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* CSV Import */}
      {showImport && (
        <CsvImportModal
          onClose={() => setShowImport(false)}
          onImported={() => load(1)}
        />
      )}

      {/* Create Lead */}
      {showCreate && (
        <CreateLeadModal
          isAdmin={isAdmin}
          users={users}
          onClose={() => setShowCreate(false)}
          onCreated={() => { show("Lead created successfully"); load(1); }}
        />
      )}

      {/* Live Transcript / Recording */}
      {transcriptLead && (
        <LiveTranscriptModal
          lead={transcriptLead}
          onClose={() => setTranscriptLead(null)}
        />
      )}
    </div>
  );
}
