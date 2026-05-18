import { useState, useEffect, useCallback } from "react";
import { Users, Plus, RefreshCw, Shield, Ban, CheckCircle, Trash2, Key } from "lucide-react";
import { api } from "../api/client";
import { Spinner }    from "../components/Spinner";
import { Modal }      from "../components/Modal";
import { Badge }      from "../components/Badge";
import { EmptyState } from "../components/EmptyState";
import { useToast }   from "../components/Toast";

// ── Role badge ───────────────────────────────────────────────────────
function RoleBadge({ role }) {
  return <Badge variant={role === "admin" ? "blue" : "gray"}>{role}</Badge>;
}

// ── Create User Modal ────────────────────────────────────────────────
function CreateUserModal({ onClose, onCreated }) {
  const [form,    setForm]    = useState({ email: "", password: "", full_name: "", role: "user" });
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      await api.admin.users.create(form);
      onCreated();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally { setLoading(false); }
  }

  const inp = "w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500";

  return (
    <Modal open onClose={onClose} title="Create User">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div><label className="text-xs text-gray-400 block mb-1">Full Name</label>
          <input className={inp} value={form.full_name} onChange={set("full_name")} required /></div>
        <div><label className="text-xs text-gray-400 block mb-1">Email</label>
          <input type="email" className={inp} value={form.email} onChange={set("email")} required /></div>
        <div><label className="text-xs text-gray-400 block mb-1">Password</label>
          <input type="password" className={inp} value={form.password} onChange={set("password")} required /></div>
        <div><label className="text-xs text-gray-400 block mb-1">Role</label>
          <select className={inp} value={form.role} onChange={set("role")}>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select></div>
        {error && <p className="text-red-400 text-xs bg-red-900/30 border border-red-800 rounded p-2">{error}</p>}
        <div className="flex gap-3 pt-1">
          <button type="button" onClick={onClose} className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">Cancel</button>
          <button type="submit" disabled={loading} className="flex-1 py-2 rounded bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium flex items-center justify-center gap-2">
            {loading ? <Spinner size={14} /> : <Plus size={14} />}
            {loading ? "Creating…" : "Create"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ── Reset Password Modal ─────────────────────────────────────────────
function ResetPasswordModal({ user, onClose, onDone }) {
  const [pw,      setPw]      = useState("");
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      await api.admin.users.resetPassword(user.id, { new_password: pw });
      onDone(`Password reset for ${user.full_name}`);
      onClose();
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return (
    <Modal open onClose={onClose} title={`Reset Password — ${user.full_name}`}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="text-xs text-gray-400 block mb-1">New Password</label>
          <input type="password" className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            value={pw} onChange={(e) => setPw(e.target.value)} required minLength={8} />
        </div>
        {error && <p className="text-red-400 text-xs bg-red-900/30 border border-red-800 rounded p-2">{error}</p>}
        <div className="flex gap-3 pt-1">
          <button type="button" onClick={onClose} className="flex-1 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm">Cancel</button>
          <button type="submit" disabled={loading} className="flex-1 py-2 rounded bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 text-sm font-medium flex items-center justify-center gap-2">
            {loading ? <Spinner size={14} /> : <Key size={14} />}
            {loading ? "Resetting…" : "Reset Password"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ── Admin Users Page ─────────────────────────────────────────────────
export default function AdminUsers() {
  const [users,       setUsers]       = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);
  const [showCreate,  setShowCreate]  = useState(false);
  const [resetTarget, setResetTarget] = useState(null);
  const { show, ToastEl } = useToast();

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.admin.users.list();
      setUsers(data.users || []);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function toggleSuspend(u) {
    try {
      if (u.is_suspended) {
        await api.admin.users.activate(u.id);
        show(`${u.full_name} activated`);
      } else {
        await api.admin.users.suspend(u.id);
        show(`${u.full_name} suspended`, "error");
      }
      load();
    } catch (e) { show(e.message, "error"); }
  }

  async function deleteUser(u) {
    if (!confirm(`Delete ${u.full_name}? This cannot be undone.`)) return;
    try {
      await api.admin.users.delete(u.id);
      show(`${u.full_name} deleted`);
      load();
    } catch (e) { show(e.message, "error"); }
  }

  return (
    <div className="space-y-6">
      {ToastEl}

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield size={22} className="text-blue-400" /> User Management
        </h1>
        <div className="flex items-center gap-3">
          <button onClick={load} className="text-gray-400 hover:text-white transition-colors"><RefreshCw size={15} /></button>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium transition-colors">
            <Plus size={14} /> New User
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : error ? (
        <div className="text-center text-red-400 py-12 text-sm">{error}</div>
      ) : users.length === 0 ? (
        <EmptyState icon={Users} title="No users yet" />
      ) : (
        <div className="bg-gray-900 rounded overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-gray-800">
                <th className="text-left p-3">Name</th>
                <th className="text-left p-3">Email</th>
                <th className="text-left p-3">Role</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Leads</th>
                <th className="text-left p-3">Calls</th>
                <th className="text-left p-3">Last Login</th>
                <th className="text-left p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
                  <td className="p-3 font-medium">{u.full_name}</td>
                  <td className="p-3 text-gray-400 text-xs">{u.email}</td>
                  <td className="p-3"><RoleBadge role={u.role} /></td>
                  <td className="p-3">
                    {u.is_suspended
                      ? <Badge variant="red">Suspended</Badge>
                      : u.is_active
                      ? <Badge variant="green">Active</Badge>
                      : <Badge variant="gray">Inactive</Badge>}
                  </td>
                  <td className="p-3 text-gray-400">{u.total_leads ?? "—"}</td>
                  <td className="p-3 text-gray-400">{u.total_calls ?? "—"}</td>
                  <td className="p-3 text-gray-500 text-xs">
                    {u.last_login ? new Date(u.last_login).toLocaleDateString() : "Never"}
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-1">
                      <button onClick={() => toggleSuspend(u)} title={u.is_suspended ? "Activate" : "Suspend"}
                        className="p-1.5 rounded hover:bg-gray-700 transition-colors">
                        {u.is_suspended
                          ? <CheckCircle size={14} className="text-green-400" />
                          : <Ban size={14} className="text-yellow-400" />}
                      </button>
                      <button onClick={() => setResetTarget(u)} title="Reset password"
                        className="p-1.5 rounded hover:bg-gray-700 transition-colors">
                        <Key size={14} className="text-blue-400" />
                      </button>
                      <button onClick={() => deleteUser(u)} title="Delete user"
                        className="p-1.5 rounded hover:bg-gray-700 transition-colors">
                        <Trash2 size={14} className="text-red-400" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate  && <CreateUserModal onClose={() => setShowCreate(false)} onCreated={load} />}
      {resetTarget && (
        <ResetPasswordModal
          user={resetTarget}
          onClose={() => setResetTarget(null)}
          onDone={(msg) => show(msg)}
        />
      )}
    </div>
  );
}
