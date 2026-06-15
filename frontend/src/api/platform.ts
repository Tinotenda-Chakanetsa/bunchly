/* Platform-admin Tenant management.
 *
 * Endpoints all live under /tenants/organisations/ and are gated by
 * IsPlatformAdmin on the backend — any non-platform-admin user will get
 * 403 before this is even reachable. */
import { api } from "./client";
import type { Paginated } from "./employees";

export interface PlatformTenantDomain {
  id: string;
  domain: string;
  is_primary: boolean;
  created_at?: string;
}

export interface PlatformTenantSettings {
  id: string;
  timezone?: string;
  locale?: string;
  primary_color?: string;
  data_retention_days?: number;
}

export interface PlatformTenant {
  id: string;
  name: string;
  slug: string;
  legal_name?: string;
  industry?: string;
  country?: string;
  is_active: boolean;
  onboarded_at?: string | null;
  domains?: PlatformTenantDomain[];
  settings?: PlatformTenantSettings;
  created_at?: string;
  updated_at?: string;
}

export async function listTenants(params: { search?: string; page?: number } = {}) {
  const { data } = await api.get<Paginated<PlatformTenant>>("/tenants/organisations/", {
    params: { page_size: 100, ...params },
  });
  return data;
}

export async function getTenant(id: string) {
  const { data } = await api.get<PlatformTenant>(`/tenants/organisations/${id}/`);
  return data;
}

export async function createTenant(payload: {
  name: string;
  legal_name?: string;
  industry?: string;
  country?: string;
}) {
  const { data } = await api.post<PlatformTenant>("/tenants/organisations/", payload);
  return data;
}

export interface ProvisionTenantInput {
  name: string;
  slug?: string;
  domain?: string;
  legal_name?: string;
  industry?: string;
  country?: string;
  admin_email: string;
  admin_first_name?: string;
  admin_last_name?: string;
  /** Optional. If omitted, the backend generates one and returns it on `one_time_password`. */
  admin_password?: string;
}

export interface ProvisionTenantResponse {
  tenant: PlatformTenant;
  admin: { id: string; email: string; created: boolean };
  /** Only set when the backend generated a password we should show once. */
  one_time_password: string | null;
  tenant_created: boolean;
}

/** One-shot provisioning: creates the tenant, copies in every system role,
 *  and creates the first Organisation Administrator user. Idempotent. */
export async function provisionTenant(payload: ProvisionTenantInput) {
  const { data } = await api.post<ProvisionTenantResponse>(
    "/tenants/organisations/provision/",
    payload,
  );
  return data;
}

export async function updateTenant(id: string, patch: Partial<PlatformTenant>) {
  const { data } = await api.patch<PlatformTenant>(
    `/tenants/organisations/${id}/`,
    patch,
  );
  return data;
}

export async function activateTenant(id: string) {
  const { data } = await api.post<{ status: string }>(
    `/tenants/organisations/${id}/activate/`,
  );
  return data;
}

export async function deactivateTenant(id: string) {
  const { data } = await api.post<{ status: string }>(
    `/tenants/organisations/${id}/deactivate/`,
  );
  return data;
}
