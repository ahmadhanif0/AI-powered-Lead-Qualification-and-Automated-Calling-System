// Centralized API client — all fetch logic lives here.
// Components and hooks import from this file only.

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const WS_BASE = import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `HTTP ${res.status}`);
  }
  // 204 No Content
  if (res.status === 204) return null;
  return res.json();
}

// ── Dashboard ────────────────────────────────────────────────────────
export const api = {
  dashboard: {
    stats:   () => request("/dashboard/stats"),
    summary: () => request("/dashboard/summary"),
  },

  // ── HubSpot ───────────────────────────────────────────────────────
  hubspot: {
    contacts:    () => request("/hubspot/contacts"),
    sync:        () => request("/hubspot/sync",       { method: "POST" }),
    syncAsync:   () => request("/hubspot/sync-async", { method: "POST" }),
  },

  // ── Assistants ────────────────────────────────────────────────────
  assistants: {
    list:   ()         => request("/assistants/"),
    get:    (id)       => request(`/assistants/${id}`),
    create: (payload)  => request("/assistants/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  },

  // ── Calls ─────────────────────────────────────────────────────────
  calls: {
    start: (leadId) => request(`/calls/start/${leadId}`, { method: "POST" }),
  },

  // ── Retries ───────────────────────────────────────────────────────
  retries: {
    list: () => request("/retries/"),
  },
};

export { WS_BASE };
