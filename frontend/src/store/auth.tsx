import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import {
  endImpersonation as apiEndImpersonation,
  fetchMe,
  impersonateTenant as apiImpersonateTenant,
  login as apiLogin,
  logout as apiLogout,
  switchTenant as apiSwitchTenant,
} from "@/api/auth";
import { tokenStore } from "@/api/client";
import { effectiveRoleFrom, type EffectiveRole } from "@/lib/effectiveRole";
import type { MembershipBrief, BunchlyUser } from "@/types/auth";

interface AuthState {
  user: BunchlyUser | null;
  memberships: MembershipBrief[];
  activeTenantId: string | null;
  activeTenantName: string | null;
  activeTenantSlug: string | null;
  permissions: Set<string>;
  /** True only when a platform admin entered a tenant via the audited
   *  impersonation flow. Drives the banner + the sidebar visibility. */
  impersonating: boolean;
  loading: boolean;
}

interface AuthApi extends AuthState {
  hasPerm: (code: string) => boolean;
  hasAnyPerm: (codes: string[]) => boolean;
  effectiveRole: EffectiveRole;
  login: (email: string, password: string, tenantSlug?: string) => Promise<void>;
  logout: () => Promise<void>;
  switchTenant: (tenantSlug: string) => Promise<void>;
  impersonateTenant: (tenantId: string) => Promise<void>;
  endImpersonation: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthApi | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    memberships: [],
    activeTenantId: null,
    activeTenantName: null,
    activeTenantSlug: null,
    permissions: new Set(),
    impersonating: false,
    loading: true,
  });

  const refresh = useCallback(async () => {
    if (!tokenStore.getAccess()) {
      setState((s) => ({
        ...s,
        user: null,
        loading: false,
        permissions: new Set(),
        impersonating: false,
        activeTenantName: null,
        activeTenantSlug: null,
      }));
      return;
    }
    try {
      const me = await fetchMe();
      setState({
        user: me.user,
        memberships: me.memberships,
        activeTenantId: me.active_tenant_id,
        activeTenantName: me.active_tenant_name ?? null,
        activeTenantSlug: me.active_tenant_slug ?? null,
        permissions: new Set(me.permissions),
        impersonating: me.impersonating === true,
        loading: false,
      });
    } catch {
      tokenStore.clear();
      setState({
        user: null,
        memberships: [],
        activeTenantId: null,
        activeTenantName: null,
        activeTenantSlug: null,
        permissions: new Set(),
        impersonating: false,
        loading: false,
      });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value: AuthApi = useMemo(
    () => ({
      ...state,
      /* Permission lookups mirror the backend's `has_perm_code`:
         platform admins bypass entirely, tenant *owners* hold the
         wildcard "*" (granted by the backend's permission_codes()), and
         everyone else needs the literal codename. */
      hasPerm: (code) =>
        state.user?.is_platform_admin === true ||
        state.permissions.has("*") ||
        state.permissions.has(code),
      hasAnyPerm: (codes) =>
        state.user?.is_platform_admin === true ||
        state.permissions.has("*") ||
        codes.some((c) => state.permissions.has(c)),
      effectiveRole: effectiveRoleFrom(state.user, state.permissions),
      login: async (email, password, tenantSlug) => {
        await apiLogin(email, password, tenantSlug);
        await refresh();
      },
      logout: async () => {
        await apiLogout();
        setState({
          user: null,
          memberships: [],
          activeTenantId: null,
          activeTenantName: null,
          activeTenantSlug: null,
          permissions: new Set(),
          impersonating: false,
          loading: false,
        });
      },
      switchTenant: async (tenantSlug) => {
        await apiSwitchTenant(tenantSlug);
        await refresh();
      },
      impersonateTenant: async (tenantId) => {
        await apiImpersonateTenant(tenantId);
        await refresh();
      },
      endImpersonation: async () => {
        await apiEndImpersonation();
        await refresh();
      },
      refresh,
    }),
    [state, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthApi {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
