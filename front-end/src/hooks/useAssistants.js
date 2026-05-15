import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export function useAssistants() {
  const [assistants, setAssistants] = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.assistants.list();
      setAssistants(data.assistants || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = useCallback(async (payload) => {
    const result = await api.assistants.create(payload);
    await load(); // refresh list
    return result;
  }, [load]);

  return { assistants, loading, error, reload: load, create };
}
