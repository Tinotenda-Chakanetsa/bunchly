import { NavLink } from "react-router-dom";
import clsx from "clsx";

import { I } from "@/components/icons";
import { Avatar } from "@/components/ui";
import { useAuth } from "@/store/auth";

import { NAV_GROUPS } from "./nav";

export default function Sidebar() {
  const {
    user,
    memberships,
    activeTenantId,
    activeTenantName,
    hasAnyPerm,
    impersonating,
  } = useAuth();
  const activeTenant = memberships.find((m) => m.tenant_id === activeTenantId);
  const isPlatformAdmin = user?.is_platform_admin === true;
  /* Spec §8.A: platform admins must not casually browse tenant HR data.
     Hide every tenant-scoped nav group unless they've explicitly entered
     a tenant via the audited impersonation flow. */
  const showTenantNav = !isPlatformAdmin || impersonating;

  return (
    <aside className="sidebar">
      <div className="brand">
        <img
          src="/favicon-32x32.png"
          srcSet="/favicon-32x32.png 1x, /android-chrome-192x192.png 2x"
          alt="Bunchly"
          width={28}
          height={28}
          className="brand-mark"
        />
        <div className="brand-name">Bunchly</div>
      </div>

      {NAV_GROUPS.map((group) => {
        if (group.platformAdminOnly && !isPlatformAdmin) return null;
        if (!group.platformAdminOnly && !showTenantNav) return null;
        const items = group.items.filter((it) => {
          if (it.platformAdminOnly && !isPlatformAdmin) return false;
          return it.permissions.length === 0 || hasAnyPerm(it.permissions);
        });
        if (items.length === 0) return null;
        return (
          <div className="nav-group" key={group.label}>
            <div className="nav-group-label">{group.label}</div>
            {items.map((item) => {
              const Icon = I[item.icon];
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === "/"}
                  className={({ isActive }) => clsx("nav-item", isActive && "active")}
                >
                  <Icon className="nav-icon" size={16} />
                  <span>{item.label}</span>
                  {item.badge !== undefined && <span className="nav-badge">{item.badge}</span>}
                  {item.comingSoon && <span className="coming-soon">Soon</span>}
                </NavLink>
              );
            })}
          </div>
        );
      })}

      <div className="sidebar-spacer" />

      <div className="sidebar-foot-links">
        <NavLink to="/help" className="nav-item">
          <I.help className="nav-icon" size={16} />
          <span>Help & support</span>
        </NavLink>
        <NavLink to="/ai" className="nav-item">
          <I.sparkle className="nav-icon" size={16} />
          <span>Bunchly AI</span>
          <span
            className="nav-badge"
            style={{ background: "var(--positive-soft)", color: "var(--positive)" }}
          >
            Beta
          </span>
        </NavLink>
      </div>

      <div className="sidebar-user">
        <Avatar name={user?.full_name || user?.email || "?"} size="sm" />
        <div className="meta">
          <div className="name">{user?.full_name || user?.email}</div>
          <div className="role">
            {isPlatformAdmin && impersonating
              ? `Impersonating · ${activeTenantName ?? activeTenant?.tenant_name ?? "—"}`
              : isPlatformAdmin
                ? "Platform admin"
                : (activeTenant?.tenant_name ?? "—")}
          </div>
        </div>
      </div>
    </aside>
  );
}
