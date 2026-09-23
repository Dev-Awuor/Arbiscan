import { useCallback, useEffect, useState } from "react";
import axios from "axios";

const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

const api = axios.create({ baseURL: BASE });

// Attach JWT access token (if any) to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401, try a one-shot refresh, else clear session.
let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    const refresh = localStorage.getItem("refresh");
    if (error.response?.status === 401 && refresh && !original._retried) {
      original._retried = true;
      try {
        refreshing =
          refreshing ||
          axios.post(`${BASE}/auth/token/refresh/`, { refresh });
        const { data } = await refreshing;
        refreshing = null;
        localStorage.setItem("access", data.access);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch {
        refreshing = null;
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        if (location.pathname.startsWith("/app")) location.assign("/login");
      }
    }
    return Promise.reject(error);
  }
);

export default api;

/* GET with a short in-memory cache, so moving between dashboard pages
   doesn't refetch. reload() always hits the API. */
const cache = new Map();

export function useApi(url, ttl = 60_000) {
  const [state, setState] = useState(() => {
    const c = cache.get(url);
    return { data: c?.data ?? null, loading: !c, error: "" };
  });

  const load = useCallback(async (force) => {
    const c = cache.get(url);
    if (!force && c && Date.now() - c.at < ttl) {
      setState({ data: c.data, loading: false, error: "" });
      return;
    }
    setState((s) => ({ ...s, loading: true, error: "" }));
    try {
      const { data } = await api.get(url);
      cache.set(url, { data, at: Date.now() });
      setState({ data, loading: false, error: "" });
    } catch {
      setState((s) => ({ ...s, loading: false, error: "Could not load data from the API." }));
    }
  }, [url, ttl]);

  useEffect(() => { load(false); }, [load]);
  return { ...state, reload: () => load(true) };
}
