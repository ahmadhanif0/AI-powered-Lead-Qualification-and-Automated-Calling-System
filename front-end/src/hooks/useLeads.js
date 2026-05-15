import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export function useLeads() {
  const [leads,   setLeads]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.dashboard.summary();
      setLeads(data.leads || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const startCall = useCallback(async (leadId) => {
    return api.calls.start(leadId);
  }, []);

  return { leads, loading, error, reload: load, startCall };
}
