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

  function store(data) {
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);
  }

  async function login(username, password) {
    const { data } = await api.post("/auth/token/", { username, password });
    store(data);
    await loadMe();
  }

  async function register(username, email, password) {
    const { data } = await api.post("/auth/register/", { username, email, password });
    store(data);
    setUser(data.user);
  }

  function logout() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    setUser(null);
  }

  return (
    <AuthCtx.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}
