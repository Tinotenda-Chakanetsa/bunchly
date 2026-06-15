import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from "axios";

const BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const ACCESS_KEY = "bunchly.access";
const REFRESH_KEY = "bunchly.refresh";
const TENANT_KEY = "bunchly.tenant";

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  getTenant: () => localStorage.getItem(TENANT_KEY),
  setTokens(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  setTenant(id: string | null) {
    if (id) localStorage.setItem(TENANT_KEY, id);
    else localStorage.removeItem(TENANT_KEY);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(TENANT_KEY);
  },
};

export const api: AxiosInstance = axios.create({
  baseURL: BASE,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const access = tokenStore.getAccess();
  if (access) config.headers.set("Authorization", `Bearer ${access}`);
  const tenant = tokenStore.getTenant();
  if (tenant) config.headers.set("X-Tenant-ID", tenant);
  return config;
});

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return null;
  try {
    // Use a raw axios call so we don't recurse through the interceptor.
    const { data } = await axios.post(`${BASE}/auth/refresh/`, { refresh });
    if (data?.access) {
      tokenStore.setTokens(data.access, data.refresh ?? refresh);
      return data.access as string;
    }
  } catch {
    /* fall through */
  }
  tokenStore.clear();
  return null;
}

api.interceptors.response.use(
  (r) => r,
  async (err: AxiosError) => {
    const original = err.config as InternalAxiosRequestConfig & { _retried?: boolean };
    if (err.response?.status === 401 && original && !original._retried) {
      original._retried = true;
      refreshInFlight ??= refreshAccessToken().finally(() => {
        refreshInFlight = null;
      });
      const fresh = await refreshInFlight;
      if (fresh) {
        original.headers?.set?.("Authorization", `Bearer ${fresh}`);
        return api.request(original);
      }
      // Refresh failed — bounce to login.
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
    }
    return Promise.reject(err);
  },
);
