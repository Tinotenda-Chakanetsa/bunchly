import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { I } from "@/components/icons";
import { Avatar, Button } from "@/components/ui";
import { useAuth } from "@/store/auth";
import { useTheme } from "@/store/theme";

import NotificationsBell from "./NotificationsBell";

export default function Topbar() {
  const { user, memberships, activeTenantId, switchTenant, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [tenantOpen, setTenantOpen] = useState(false);

  const activeTenant = memberships.find((m) => m.tenant_id === activeTenantId);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="topbar">
      <div className="search">
        <span className="icon">
          <I.search size={15} />
        </span>
        <input placeholder="Search people, claims, documents…" />
        <span className="kbd">⌘F</span>
      </div>

      <div className="actions">
        {memberships.length > 1 && (
          <div style={{ position: "relative" }}>
            <button className="date-range" onClick={() => setTenantOpen((o) => !o)}>
              <I.building size={13} />
              <span>{activeTenant?.tenant_name ?? "Select organisation"}</span>
              <I.chevronDown size={12} />
            </button>
            {tenantOpen && (
              <>
                <div
                  onClick={() => setTenantOpen(false)}
                  style={{ position: "fixed", inset: 0, zIndex: 30 }}
                />
                <div
                  className="pop"
                  style={{
                    position: "absolute",
                    top: 40,
                    right: 0,
                    width: 240,
                    background: "var(--card)",
                    border: "1px solid var(--hairline)",
                    borderRadius: 12,
                    boxShadow: "var(--shadow-pop)",
                    zIndex: 40,
                    overflow: "hidden",
                  }}
                >
                  {memberships.map((m) => (
                    <button
                      key={m.id}
                      className="list-row clickable"
                      style={{ width: "100%", border: "none" }}
                      onClick={async () => {
                        setTenantOpen(false);
                        await switchTenant(m.tenant_slug);
                      }}
                    >
                      <div className="row-main">
                        <div className="row-title">{m.tenant_name}</div>
                        <div className="row-sub">{m.tenant_slug}</div>
                      </div>
                      {m.tenant_id === activeTenantId && <I.check size={14} />}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        <button className="icon-btn" title="Toggle theme" onClick={toggle}>
          {theme === "dark" ? <I.sun size={16} /> : <I.moon size={16} />}
        </button>

        <NotificationsBell />

        <div style={{ position: "relative" }}>
          <button
            className="icon-btn"
            onClick={() => setMenuOpen((o) => !o)}
            title="Account menu"
            style={{ width: "auto", padding: "0 6px", gap: 8 }}
          >
            <Avatar name={user?.full_name || user?.email || "?"} size="sm" />
          </button>
          {menuOpen && (
            <>
              <div
                onClick={() => setMenuOpen(false)}
                style={{ position: "fixed", inset: 0, zIndex: 30 }}
              />
              <div
                className="pop"
                style={{
                  position: "absolute",
                  top: 42,
                  right: 0,
                  width: 220,
                  background: "var(--card)",
                  border: "1px solid var(--hairline)",
                  borderRadius: 12,
                  boxShadow: "var(--shadow-pop)",
                  zIndex: 40,
                  padding: 6,
                }}
              >
                <div style={{ padding: 10, borderBottom: "1px solid var(--hairline-2)" }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{user?.full_name || user?.email}</div>
                  <div style={{ fontSize: 11, color: "var(--text-3)" }}>{user?.email}</div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  style={{ width: "100%", justifyContent: "flex-start", marginTop: 4 }}
                  onClick={() => {
                    setMenuOpen(false);
                    handleLogout();
                  }}
                >
                  <I.logout size={14} /> Sign out
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
