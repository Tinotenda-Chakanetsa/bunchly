import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuth } from "@/store/auth";

export default function RequireAuth({
  children,
  permissions,
  platformAdmin,
}: {
  children: ReactNode;
  permissions?: string[];
  /** If true, restrict to platform super-admins regardless of tenant perms. */
  platformAdmin?: boolean;
}) {
  const { user, loading, hasAnyPerm } = useAuth();
  const loc = useLocation();

  if (loading) {
    return (
      <div style={{ padding: 40, color: "var(--text-3)", fontSize: 13 }}>Loading Bunchly…</div>
    );
  }
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;

  if (platformAdmin && !user.is_platform_admin) {
    return (
      <div className="page">
        <div className="empty">
          <div className="title">Platform administrators only</div>
          <div className="lede">
            This area manages the Bunchly platform itself. Sign in as a
            platform super-admin to continue.
          </div>
        </div>
      </div>
    );
  }

  if (permissions?.length && !hasAnyPerm(permissions)) {
    return (
      <div className="page">
        <div className="empty">
          <div className="title">You don't have access to this page</div>
          <div className="lede">
            Ask your organisation administrator to grant the required permission.
          </div>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}
