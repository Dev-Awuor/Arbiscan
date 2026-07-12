import { createContext, useContext, useEffect, useState } from "react";
import api from "./api";

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  async function loadMe() {
    if (!localStorage.getItem("access")) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get("/auth/me/");
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMe();
  }, []);

  async function login(username, password) {
    const { data } = await api.post("/auth/token/", { username, password });
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);
    await loadMe();
  }

  async function register(username, email, password) {
    const { data } = await api.post("/auth/register/", { username, email, password });
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);
    setUser(data.user);
  }

  function logout() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    setUser(null);
  }

  const isPremium = !!user?.subscription?.is_premium;

  return (
    <AuthCtx.Provider value={{ user, loading, isPremium, login, register, logout, refresh: loadMe }}>
      {children}
    </AuthCtx.Provider>
  );
}
