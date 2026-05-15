import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";

export function useRetries() {
  const [retries, setRetries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.retries.list();
      setRetries(data || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { retries, loading, error, reload: load };
}
