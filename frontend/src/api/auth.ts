import { api, tokenStore } from "./client";
import type { LoginResponse, MeResponse } from "@/types/auth";

export async function login(email: string, password: string, tenantSlug?: string) {
  const { data } = await api.post<LoginResponse>("/auth/login/", {
    email,
    password,
    tenant_slug: tenantSlug,
  });
  tokenStore.setTokens(data.access, data.refresh);
  tokenStore.setTenant(data.active_tenant_id);
  return data;
}

export async function fetchMe(): Promise<MeResponse> {
  const { data } = await api.get<MeResponse>("/auth/me/");
  return data;
}

export async function switchTenant(tenantSlug: string) {
  const { data } = await api.post<{ access: string; refresh?: string; active_tenant_id: string }>(
    "/auth/switch-tenant/",
    { tenant_slug: tenantSlug },
  );
  // Refresh is optional in the response — keep the existing one when omitted.
  if (data.refresh) tokenStore.setTokens(data.access, data.refresh);
  else {
    const existingRefresh = tokenStore.getRefresh() ?? "";
    tokenStore.setTokens(data.access, existingRefresh);
  }
  tokenStore.setTenant(data.active_tenant_id);
  return data;
}

export async function logout() {
  const refresh = tokenStore.getRefresh();
  try {
    if (refresh) await api.post("/auth/logout/", { refresh });
  } finally {
    tokenStore.clear();
  }
}

/* --- Platform admin impersonation (audited) --- */

export interface ImpersonationStartResponse {
  access: string;
  refresh: string;
  active_tenant_id: string;
  tenant_slug: string;
  tenant_name: string;
  impersonating: true;
}

export async function impersonateTenant(tenantId: string): Promise<ImpersonationStartResponse> {
  const { data } = await api.post<ImpersonationStartResponse>(
    `/tenants/organisations/${tenantId}/impersonate/`,
  );
  tokenStore.setTokens(data.access, data.refresh);
  tokenStore.setTenant(data.active_tenant_id);
  return data;
}

export async function endImpersonation(): Promise<void> {
  const { data } = await api.post<{ access: string; refresh: string; active_tenant_id: null }>(
    "/auth/end-impersonation/",
  );
  tokenStore.setTokens(data.access, data.refresh);
  tokenStore.setTenant(null);
}
