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
      }
    }
    return Promise.reject(error);
  }
);

export default api;
