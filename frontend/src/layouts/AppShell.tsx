import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { I } from "@/components/icons";
import { Button, useToast } from "@/components/ui";
import { useAuth } from "@/store/auth";

import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

/* Persistent yellow banner shown across the entire app while a platform
   admin has impersonated a tenant. Mandatory UX in any audited
   impersonation flow — the human at the keyboard must never lose track
   of whose data they're looking at. */
function ImpersonationBanner() {
  const navigate = useNavigate();
  const toast = useToast();
  const { activeTenantName, activeTenantSlug, endImpersonation } = useAuth();
  const [exiting, setExiting] = useState(false);

  async function exit() {
    setExiting(true);
    try {
      await endImpersonation();
      toast.push("Exited impersonation", "success");
      navigate("/platform/tenants");
    } catch {
      toast.push("Could not exit impersonation", "error");
    } finally {
      setExiting(false);
    }
  }

  return (
    <div
      style={{
        background: "var(--yellow)",
        color: "var(--ink-3)",
        padding: "8px 18px",
        display: "flex",
        alignItems: "center",
        gap: 12,
        fontSize: 13,
        fontWeight: 500,
        borderBottom: "1px solid var(--yellow-deep)",
      }}
      role="alert"
    >
      <I.shield size={14} />
      <span>
        <strong>You are impersonating</strong>{" "}
        {activeTenantName ?? activeTenantSlug ?? "this tenant"}. Every action
        you take is recorded in this tenant's audit log under your platform
        admin account.
      </span>
      <Button
        variant="ink"
        size="sm"
        onClick={exit}
        disabled={exiting}
        style={{ marginLeft: "auto" }}
      >
        {exiting ? "Exiting…" : "Exit impersonation"}
      </Button>
    </div>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const { impersonating } = useAuth();
  return (
    <div className="app">
      <Sidebar />
      <div className="main">
        {impersonating && <ImpersonationBanner />}
        <Topbar />
        {children}
      </div>
    </div>
  );
}
