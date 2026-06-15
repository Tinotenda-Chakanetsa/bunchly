export interface BunchlyUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  is_platform_admin: boolean;
}

export interface MembershipBrief {
  id: string;
  tenant_id: string;
  tenant_slug: string;
  tenant_name: string;
  is_owner: boolean;
  is_default: boolean;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: BunchlyUser;
  active_tenant_id: string | null;
  memberships: MembershipBrief[];
}

export interface MeResponse {
  user: BunchlyUser;
  memberships: MembershipBrief[];
  active_tenant_id: string | null;
  active_tenant_name?: string | null;
  active_tenant_slug?: string | null;
  permissions: string[];
  /** True when a platform admin has explicitly entered this tenant via the
   *  audited impersonation flow (POST /tenants/organisations/:id/impersonate/). */
  impersonating?: boolean;
}
