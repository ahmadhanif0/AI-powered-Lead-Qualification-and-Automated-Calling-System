import { useState, useCallback } from "react";

/**
 * Generic hook for async operations.
 * Returns { data, loading, error, run }
 * `run` accepts a promise-returning function and optional args.
 */
export function useAsync(fn, immediate = false) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(immediate);
  const [error,   setError]   = useState(null);

  const run = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fn(...args);
      setData(result);
      return result;
    } catch (e) {
      setError(e.message || "Unknown error");
      throw e;
    } finally {
      setLoading(false);
    }
  }, [fn]);

  return { data, loading, error, run };
}
