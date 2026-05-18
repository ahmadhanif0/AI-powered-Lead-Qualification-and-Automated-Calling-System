// Centralized API client — injects Bearer token, auto-refreshes on 401.

const BASE    = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const WS_BASE = import.meta.env.VITE_WS_URL  || "ws://127.0.0.1:8000";

// ── Token storage ────────────────────────────────────────────────────
export const tokenStore = {
  getAccess:  ()     => localStorage.getItem("access_token"),
  getRefresh: ()     => localStorage.getItem("refresh_token"),
  setTokens:  (a, r) => { localStorage.setItem("access_token", a); if (r) localStorage.setItem("refresh_token", r); },
  clear:      ()     => { ["access_token","refresh_token","user"].forEach(k => localStorage.removeItem(k)); },
  getUser:    ()     => { try { return JSON.parse(localStorage.getItem("user")); } catch { return null; } },
  setUser:    (u)    => localStorage.setItem("user", JSON.stringify(u)),
};

// ── Core fetch ───────────────────────────────────────────────────────
async function request(path, options = {}) {
  const token = tokenStore.getAccess();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    const ok = await tryRefresh();
    if (ok) {
      const h2 = { ...headers, Authorization: `Bearer ${tokenStore.getAccess()}` };
      const r2 = await fetch(`${BASE}${path}`, { ...options, headers: h2 });
      if (!r2.ok) throw new Error((await r2.text()) || `HTTP ${r2.status}`);
      if (r2.status === 204) return null;
      return r2.json();
    }
    tokenStore.clear();
    window.location.href = "/login";
    throw new Error("Session expired");
  }

  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  if (res.status === 204) return null;
  return res.json();
}

// Multipart upload (no Content-Type header — browser sets boundary)
async function upload(path, formData) {
  const token = tokenStore.getAccess();
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) throw new Error((await res.text()) || `HTTP ${res.status}`);
  return res.json();
}

async function tryRefresh() {
  const rt = tokenStore.getRefresh();
  if (!rt) return false;
  try {
    const r = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: rt }),
    });
    if (!r.ok) return false;
    const d = await r.json();
    tokenStore.setTokens(d.access_token, null);
    return true;
  } catch { return false; }
}

// ── API surface ──────────────────────────────────────────────────────
export const api = {

  auth: {
    signup:  (b) => request("/auth/signup",  { method: "POST", body: JSON.stringify(b) }),
    login:   (b) => request("/auth/login",   { method: "POST", body: JSON.stringify(b) }),
    refresh: (b) => request("/auth/refresh", { method: "POST", body: JSON.stringify(b) }),
    logout:  ()  => request("/auth/logout",  { method: "POST" }),
    me:      ()  => request("/auth/me"),
  },

  dashboard: {
    stats:   () => request("/dashboard/stats"),
    summary: () => request("/dashboard/summary"),
  },

  leads: {
    list:             (p = {}) => { const q = new URLSearchParams(p).toString(); return request(`/leads${q ? `?${q}` : ""}`); },
    get:              (id)     => request(`/leads/${id}`),
    create:           (b)      => request("/leads/create", { method: "POST", body: JSON.stringify(b) }),
    update:           (id, b)  => request(`/leads/${id}`, { method: "PUT",    body: JSON.stringify(b) }),
    delete:           (id)     => request(`/leads/${id}`, { method: "DELETE" }),
    uploadCsv:        (file)   => { const fd = new FormData(); fd.append("file", file); return upload("/leads/upload-csv", fd); },
    downloadTemplate: ()       => `${BASE}/leads/download-template`,
  },

  hubspot: {
    contacts:  () => request("/hubspot/contacts"),
    sync:      () => request("/hubspot/sync",       { method: "POST" }),
    syncAsync: () => request("/hubspot/sync-async", { method: "POST" }),
    // OAuth
    oauth: {
      connect:      () => request("/crm/hubspot/connect"),
      status:       () => request("/crm/hubspot/status"),
      refreshToken: () => request("/crm/hubspot/refresh-token", { method: "POST" }),
      disconnect:   () => request("/crm/hubspot/disconnect",    { method: "DELETE" }),
    },
  },

  crm: {
    connections: ()        => request("/crm/connections"),
    connect:     (b)       => request("/crm/connect",              { method: "POST",   body: JSON.stringify(b) }),
    disconnect:  (id)      => request(`/crm/connections/${id}`,    { method: "DELETE" }),
    sync:        ()        => request("/crm/sync",                 { method: "POST" }),
  },

  assistants: {
    list:   ()        => request("/assistants/"),
    get:    (id)      => request(`/assistants/${id}`),
    create: (b)       => request("/assistants/", { method: "POST", body: JSON.stringify(b) }),
    update: (id, b)   => request(`/assistants/${id}`, { method: "PUT",    body: JSON.stringify(b) }),
    delete: (id)      => request(`/assistants/${id}`, { method: "DELETE" }),
  },

  calls: {
    start:           (leadId) => request(`/calls/start/${leadId}`, { method: "POST" }),
    schedule:        (b)      => request("/calls/schedule",        { method: "POST", body: JSON.stringify(b) }),
    scheduled:       ()       => request("/calls/scheduled"),
    cancelScheduled: (id)     => request(`/calls/scheduled/${id}`, { method: "DELETE" }),
    recording:       (callId) => request(`/users/calls/${callId}/recording`),
  },

  retries: {
    list: () => request("/retries/"),
  },

  retryConfigs: {
    list:   ()           => request("/retry-configs/"),
    update: (type, body) => request(`/retry-configs/${type}`, { method: "PUT", body: JSON.stringify(body) }),
  },

  users: {
    notificationSettings:       ()  => request("/users/notification-settings"),
    updateNotificationSettings: (b) => request("/users/notification-settings", { method: "PUT", body: JSON.stringify(b) }),
  },

  admin: {
    leads: {
      list:   (p = {}) => { const q = new URLSearchParams(p).toString(); return request(`/admin/leads${q ? `?${q}` : ""}`); },
      get:    (id)     => request(`/admin/leads/${id}`),
      update: (id, b)  => request(`/admin/leads/${id}`, { method: "PUT",    body: JSON.stringify(b) }),
      delete: (id)     => request(`/admin/leads/${id}`, { method: "DELETE" }),
    },
    users: {
      list:          (p = {}) => { const q = new URLSearchParams(p).toString(); return request(`/admin/users${q ? `?${q}` : ""}`); },
      create:        (b)      => request("/admin/users",                        { method: "POST",   body: JSON.stringify(b) }),
      update:        (id, b)  => request(`/admin/users/${id}`,                  { method: "PUT",    body: JSON.stringify(b) }),
      delete:        (id)     => request(`/admin/users/${id}`,                  { method: "DELETE" }),
      suspend:       (id)     => request(`/admin/users/${id}/suspend`,           { method: "POST" }),
      activate:      (id)     => request(`/admin/users/${id}/activate`,          { method: "POST" }),
      resetPassword: (id, b)  => request(`/admin/users/${id}/reset-password`,   { method: "POST",   body: JSON.stringify(b) }),
      activity:      (id, p)  => { const q = new URLSearchParams(p).toString(); return request(`/admin/users/${id}/activity${q ? `?${q}` : ""}`); },
    },
    assistants: {
      all:     (p = {}) => { const q = new URLSearchParams(p).toString(); return request(`/admin/assistants/all${q ? `?${q}` : ""}`); },
      history: (id)     => request(`/admin/assistants/${id}/history`),
    },
    celery: {
      failedJobs: () => request("/admin/celery/failed-jobs"),
    },
    analytics: {
      overview:   ()   => request("/admin/analytics/overview"),
      user:       (id) => request(`/admin/analytics/users/${id}`),
      assistants: ()   => request("/admin/analytics/assistants"),
      global:     ()   => request("/admin/analytics/global"),
    },
  },
};

export { WS_BASE };
