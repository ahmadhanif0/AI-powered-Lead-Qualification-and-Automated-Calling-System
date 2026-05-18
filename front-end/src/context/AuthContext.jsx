import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api, tokenStore } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(() => tokenStore.getUser());
  const [loading, setLoading] = useState(true);

  // On mount, verify the stored token is still valid
  useEffect(() => {
    const token = tokenStore.getAccess();
    if (!token) { setLoading(false); return; }

    api.auth.me()
      .then((u) => { setUser(u); tokenStore.setUser(u); })
      .catch(() => { tokenStore.clear(); setUser(null); })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await api.auth.login({ email, password });
    tokenStore.setTokens(data.access_token, data.refresh_token);
    tokenStore.setUser(data.user);
    setUser(data.user);
    return data.user;
  }, []);

  const signup = useCallback(async (email, password, full_name) => {
    const data = await api.auth.signup({ email, password, full_name });
    tokenStore.setTokens(data.access_token, data.refresh_token);
    tokenStore.setUser(data.user);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try { await api.auth.logout(); } catch { /* ignore */ }
    tokenStore.clear();
    setUser(null);
  }, []);

  const isAdmin = user?.role === "admin";

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, isAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
