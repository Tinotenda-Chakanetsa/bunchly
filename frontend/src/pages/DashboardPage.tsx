import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { CSSProperties, ReactNode } from "react";

import { I, type IconName } from "@/components/icons";
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardHead,
  KpiCell,
  KpiStrip,
  Meter,
  PersonCell,
  StatusBadge,
  useToast,
} from "@/components/ui";
import * as Demo from "@/lib/demo";
import { fmtDateShort } from "@/lib/format";
import { downloadCsv } from "@/lib/export";
import { useStore } from "@/lib/store";
import { useQuery } from "@tanstack/react-query";
import { listEmployees } from "@/api/employees";
import { listLeaveRequests } from "@/api/leave";
import { listEducationClaims } from "@/api/education";
import { listDocuments } from "@/api/documents";
import {
  listAuditLog,
  listCandidates,
  listHRCases,
  listJobRequisitions,
  listPolicies,
} from "@/api/hr";
import { listProgrammes } from "@/api/onboarding";
import { useAuth } from "@/store/auth";

/* ============================================
 * Live activity helpers (drive Headcount flow + Recent activity)
 * ============================================ */

interface ActivityRow {
  id: string;
  who: string;
  av: string;
  action: string;
  date: string;
  ts: number;
  type: "leave" | "claim" | "doc" | "req" | "ob" | "policy" | "case" | "asset" | "other";
  detail: string;
  status: string;
  iconBg: string;
  iconColor: string;
}

const ACTIVITY_TYPE_LABEL: Record<ActivityRow["type"], string> = {
  leave: "Leave",
  claim: "Claim",
  doc: "Document",
  req: "Requisition",
  ob: "Onboarding",
  policy: "Policy",
  case: "HR case",
  asset: "Asset",
  other: "Other",
};

const ACTIVITY_TYPE_THEME: Record<
  ActivityRow["type"],
  { bg: string; color: string; status: string }
> = {
  leave: { bg: "var(--info-soft)", color: "var(--action)", status: "Pending Approval" },
  claim: { bg: "var(--yellow-soft)", color: "var(--yellow-deep)", status: "Pending HR" },
  doc: { bg: "var(--positive-soft)", color: "var(--positive)", status: "Pending Review" },
  req: { bg: "var(--mist)", color: "var(--ink-3)", status: "Open" },
  ob: { bg: "var(--positive-soft)", color: "var(--positive)", status: "In Progress" },
  policy: { bg: "var(--mist)", color: "var(--ink-3)", status: "Open" },
  case: { bg: "var(--yellow-soft)", color: "var(--yellow-deep)", status: "Open" },
  asset: { bg: "var(--info-soft)", color: "var(--action)", status: "Verified" },
  other: { bg: "var(--mist)", color: "var(--text-3)", status: "Open" },
};

function classifyAction(action: string): ActivityRow["type"] {
  const a = action.toLowerCase();
  if (a.includes("leave")) return "leave";
  if (a.includes("claim")) return "claim";
  if (a.includes("document") || a.includes("uploaded")) return "doc";
  if (a.includes("requisition") || a.includes("posting")) return "req";
  if (a.includes("onboard") || a.includes("programme") || a.includes("task")) return "ob";
  if (a.includes("policy") || a.includes("acknow")) return "policy";
  if (a.includes("case")) return "case";
  if (a.includes("asset")) return "asset";
  return "other";
}

function parseAuditTs(at: string): number {
  // store.ts writes "YYYY-MM-DD HH:MM"
  const d = new Date(at.replace(" ", "T"));
  const ms = d.getTime();
  return Number.isFinite(ms) ? ms : Date.now();
}

function timeAgo(ms: number): string {
  const diff = Math.max(0, Date.now() - ms);
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "Just now";
  if (min < 60) return `${min} min ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} hr${hr === 1 ? "" : "s"} ago`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day} day${day === 1 ? "" : "s"} ago`;
  return new Date(ms).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
}

export default function DashboardPage() {
  const { effectiveRole } = useAuth();
  return (
    <div className="page">
      {effectiveRole === "hr" && <HRDashboard />}
      {effectiveRole === "manager" && <ManagerDashboard />}
      {effectiveRole === "employee" && <EmployeeDashboard />}
    </div>
  );
}

/* ============================================
 * Shared building blocks (ported from prototype)
 * ============================================ */
interface HeroAction {
  label: string;
  icon: ReactNode;
  primary?: boolean;
  onClick?: () => void;
}

function HeroCard({
  eyebrow,
  big,
  delta,
  sub,
  actions,
}: {
  eyebrow: ReactNode;
  big: ReactNode;
  delta?: ReactNode;
  sub?: ReactNode;
  actions: HeroAction[];
}) {
  return (
    <div className="hero-card">
      <div className="hero-bg-mark">B</div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          gap: 24,
          position: "relative",
          zIndex: 1,
        }}
      >
        <div>
          <span style={{ fontSize: 12, color: "rgba(255,255,255,0.65)", fontWeight: 500 }}>
            {eyebrow}
          </span>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginTop: 4 }}>
            <span
              style={{
                fontSize: 38,
                fontWeight: 600,
                letterSpacing: "-0.02em",
                lineHeight: 1,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {big}
            </span>
            {delta && (
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--yellow)" }}>
                {delta}{" "}
                <I.arrow
                  size={12}
                  style={{ verticalAlign: "-1px", transform: "rotate(-45deg)" }}
                />
              </span>
            )}
          </div>
          {sub && (
            <div style={{ fontSize: 12, color: "rgba(255,255,255,0.55)", marginTop: 6 }}>{sub}</div>
          )}
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {actions.map((a, i) => (
            <button
              key={i}
              onClick={a.onClick}
              className="btn btn-sm"
              style={{
                background: a.primary ? "var(--yellow)" : "rgba(255,255,255,0.08)",
                color: a.primary ? "var(--ink-3)" : "#fff",
                border: a.primary ? "none" : "1px solid rgba(255,255,255,0.12)",
                fontWeight: a.primary ? 600 : 500,
                height: 32,
              }}
            >
              {a.icon} {a.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function SegmentedSm({
  options,
  value,
  onChange,
}: {
  options: string[];
  value: string;
  onChange?: (v: string) => void;
}) {
  return (
    <div
      style={{
        display: "inline-flex",
        background: "var(--mist)",
        border: "1px solid var(--hairline)",
        borderRadius: 8,
        padding: 2,
      }}
    >
      {options.map((o) => (
        <button
          key={o}
          onClick={() => onChange?.(o)}
          style={{
            padding: "4px 10px",
            fontSize: 11.5,
            fontWeight: 500,
            color: o === value ? "var(--ink-3)" : "var(--text-3)",
            background: o === value ? "var(--card)" : "transparent",
            borderRadius: 6,
            boxShadow: o === value ? "0 1px 2px rgba(20,30,44,0.08)" : "none",
            cursor: "pointer",
            border: "none",
          }}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

function BiBarChart({
  series,
  labels,
}: {
  series: Array<{ v: number; neg: number }>;
  labels: string[];
}) {
  const max = Math.max(...series.map((s) => Math.max(s.v, s.neg))) || 1;
  const w = 100 / series.length;
  return (
    <div style={{ position: "relative", height: 200 }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          pointerEvents: "none",
        }}
      >
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ height: 1, background: "var(--hairline-2)" }} />
        ))}
      </div>
      <div
        style={{
          position: "absolute",
          left: -28,
          top: 0,
          bottom: 24,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          fontSize: 10,
          color: "var(--text-3)",
        }}
      >
        <span>{max}</span>
        <span>0</span>
        <span>−{Math.ceil(max / 2)}</span>
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: "60%",
          height: 1,
          background: "var(--hairline)",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: "0 0 24px 0",
          display: "flex",
          alignItems: "stretch",
        }}
      >
        {series.map((s, i) => {
          const posH = (s.v / max) * 60;
          const negH = (s.neg / max) * 40;
          return (
            <div key={i} style={{ width: `${w}%`, position: "relative" }}>
              <div
                style={{
                  position: "absolute",
                  left: 1,
                  right: 1,
                  top: `${60 - posH}%`,
                  height: `${posH}%`,
                  background: "var(--ink-3)",
                  borderRadius: "2px 2px 0 0",
                  minHeight: 2,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: 1,
                  right: 1,
                  top: "60%",
                  height: `${negH}%`,
                  background: "var(--bunchly)",
                  borderRadius: "0 0 2px 2px",
                  minHeight: s.neg > 0 ? 2 : 0,
                }}
              />
            </div>
          );
        })}
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          display: "flex",
          justifyContent: "space-between",
          fontSize: 10.5,
          color: "var(--text-3)",
          paddingTop: 6,
        }}
      >
        {labels.map((l) => (
          <span key={l}>{l}</span>
        ))}
      </div>
    </div>
  );
}

function SideMetric({
  icon,
  iconBg,
  iconColor,
  label,
  value,
  delta,
  deltaTone,
  divider,
}: {
  icon: ReactNode;
  iconBg: string;
  iconColor: string;
  label: string;
  value: string;
  delta: string;
  deltaTone: "up" | "down" | "flat";
  divider?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 2px",
        borderTop: divider ? "1px solid var(--hairline-2)" : "none",
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 10,
          background: iconBg,
          color: iconColor,
          display: "grid",
          placeItems: "center",
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 11.5, color: "var(--text-3)" }}>{label}</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 2 }}>
          <span
            style={{
              fontSize: 19,
              fontWeight: 600,
              color: "var(--ink-3)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {value}
          </span>
          <span className={`delta-pill ${deltaTone}`} style={{ fontSize: 10.5 }}>
            {delta}
          </span>
        </div>
      </div>
    </div>
  );
}

function ActivityIcon({
  type,
  bg,
  color,
}: {
  type: "leave" | "claim" | "doc" | "req" | "ob";
  bg: string;
  color: string;
}) {
  const map: Record<string, ReactNode> = {
    leave: <I.calendar size={13} />,
    claim: <I.money size={13} />,
    doc: <I.document size={13} />,
    req: <I.briefcase size={13} />,
    ob: <I.rocket size={13} />,
  };
  return (
    <div
      style={{
        width: 28,
        height: 28,
        borderRadius: 8,
        background: bg,
        color,
        display: "grid",
        placeItems: "center",
        flexShrink: 0,
      }}
    >
      {map[type] ?? <I.bell size={13} />}
    </div>
  );
}

function InboxRow({
  icon,
  bg,
  color,
  label,
  sub,
  onClick,
}: {
  icon: ReactNode;
  bg: string;
  color: string;
  label: ReactNode;
  sub: ReactNode;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 10px",
        borderRadius: 10,
        background: "transparent",
        textAlign: "left",
        cursor: "pointer",
        border: "1px solid transparent",
        transition: "background 0.1s, border-color 0.1s",
        width: "100%",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "var(--card-2)";
        e.currentTarget.style.borderColor = "var(--hairline-2)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent";
        e.currentTarget.style.borderColor = "transparent";
      }}
    >
      <div
        style={{
          width: 30,
          height: 30,
          borderRadius: 8,
          background: bg,
          color,
          display: "grid",
          placeItems: "center",
        }}
      >
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 500, fontSize: 12.5, color: "var(--ink-3)" }}>{label}</div>
        <div style={{ fontSize: 11, color: "var(--text-3)" }}>{sub}</div>
      </div>
      <I.chevron size={14} style={{ color: "var(--text-4)" }} />
    </button>
  );
}

/* ============================================
 * HR DASHBOARD
 * ============================================ */
function HRDashboard() {
  const navigate = useNavigate();

  /* Every dashboard collection is a small list query — page_size kept low
     because we only need the most-recent items to compute the activity feed
     and the headline counts. */
  const leaveQ = useQuery({
    queryKey: ["leave-requests", "dashboard"],
    queryFn: () => listLeaveRequests({ page: 1 }),
  });
  const claimsQ = useQuery({
    queryKey: ["education-claims", "dashboard"],
    queryFn: () => listEducationClaims({ page: 1 }),
  });
  const documentsQ = useQuery({
    queryKey: ["documents", "dashboard"],
    queryFn: () => listDocuments({ page: 1 }),
  });
  const employeesQ = useQuery({
    queryKey: ["employees"],
    queryFn: () => listEmployees(),
  });
  const reqsQ = useQuery({
    queryKey: ["job-requisitions", "dashboard"],
    queryFn: () => listJobRequisitions({ page: 1 }),
  });
  const casesQ = useQuery({
    queryKey: ["hr-cases", "dashboard"],
    queryFn: () => listHRCases({ page: 1 }),
  });
  const candidatesQ = useQuery({
    queryKey: ["candidates", "dashboard"],
    queryFn: () => listCandidates({ page: 1 }),
  });
  const programmesQ = useQuery({
    queryKey: ["onboarding-programmes", "dashboard"],
    queryFn: () => listProgrammes({}),
  });
  const policiesQ = useQuery({
    queryKey: ["policies", "dashboard"],
    queryFn: () => listPolicies({ page: 1 }),
  });
  const auditQ = useQuery({
    queryKey: ["audit", "dashboard"],
    queryFn: () => listAuditLog({ page: 1, page_size: 200 }),
  });

  const leaveRequests = leaveQ.data?.results ?? [];
  const educationClaims = claimsQ.data?.results ?? [];
  const documents = documentsQ.data?.results ?? [];
  const employees = employeesQ.data?.results ?? [];
  const jobReqs = reqsQ.data?.results ?? [];
  const hrCases = casesQ.data?.results ?? [];
  const candidates = candidatesQ.data?.results ?? [];
  const onboardingProgrammes = programmesQ.data?.results ?? [];
  const policies = policiesQ.data?.results ?? [];
  const auditLogs = auditQ.data?.results ?? [];

  const pendingLeave = leaveRequests.filter((r) =>
    /pending|submitted/i.test(r.status),
  );
  const pendingClaims = educationClaims.filter((c) =>
    /pending|submitted/i.test(c.status),
  );
  const pendingDocs = documents.filter((d) => d.status === "pending_review");
  const pendingClaimsTotal = pendingClaims.reduce(
    (a, c) => a + Number(c.amount_claimed || 0),
    0,
  );
  const today = new Date().toISOString().slice(0, 10);
  const onLeaveToday = leaveRequests.filter((r) => {
    if (r.status !== "approved" && r.status !== "Approved") return false;
    return r.start_date <= today && r.end_date >= today;
  }).length;
  const openReqs = jobReqs.filter((r) => r.status === "open" || r.status === "Open").length;

  /* ----- Recent activity (live, sortable, filterable) ----- */
  const [activityType, setActivityType] = useState<"all" | ActivityRow["type"]>("all");
  const [activitySort, setActivitySort] = useState<"newest" | "oldest">("newest");
  const [activityMenuOpen, setActivityMenuOpen] = useState(false);

  // Build avatar map for quick lookup — keyed by full_name from the live roster.
  const avByName = useMemo(() => {
    const m = new Map<string, string>();
    employees.forEach((e, i) => m.set(e.full_name, `av-${(i % 8) + 1}`));
    m.set("System", "av-8");
    m.set("Admin", "av-7");
    m.set("HR", "av-7");
    return m;
  }, [employees]);

  const recentActivity = useMemo<ActivityRow[]>(() => {
    const rows: ActivityRow[] = [];

    function push(p: {
      id: string;
      who: string;
      action: string;
      ts: number;
      type: ActivityRow["type"];
      entityId: string;
      status: string;
    }) {
      const theme = ACTIVITY_TYPE_THEME[p.type];
      rows.push({
        id: p.id,
        who: p.who,
        av: avByName.get(p.who) || "av-3",
        action: p.action,
        date: timeAgo(p.ts),
        ts: p.ts,
        type: p.type,
        detail: `${ACTIVITY_TYPE_LABEL[p.type]} · ${p.entityId.slice(0, 8)}`,
        status: p.status,
        iconBg: theme.bg,
        iconColor: theme.color,
      });
    }

    leaveRequests.forEach((r) => {
      push({
        id: `lr-${r.id}`,
        who: r.employee_name || "Employee",
        action: `Submitted ${(r.leave_type_name || "leave").toLowerCase()} · ${r.days_requested}d`,
        ts: r.submitted_at ? new Date(r.submitted_at).getTime() : new Date(r.created_at).getTime(),
        type: "leave",
        entityId: r.id,
        status: r.status_display || r.status,
      });
    });

    educationClaims.forEach((c) => {
      push({
        id: `ec-${c.id}`,
        who: c.employee_name || "Employee",
        action: `Submitted claim · $${Number(c.amount_claimed || 0).toLocaleString()}`,
        ts: c.submitted_at ? new Date(c.submitted_at).getTime() : Date.now(),
        type: "claim",
        entityId: c.id,
        status: c.status_display || c.status,
      });
    });

    documents.forEach((d) => {
      push({
        id: `doc-${d.id}`,
        who: d.employee_name || "HR",
        action: `Uploaded ${(d.category_name || "document").toLowerCase()}`,
        ts: new Date(d.created_at).getTime(),
        type: "doc",
        entityId: d.id,
        status: d.status_display || d.status,
      });
    });

    candidates.forEach((c) => {
      const who = c.full_name || `${c.first_name ?? ""} ${c.last_name ?? ""}`.trim() || "Candidate";
      push({
        id: `cand-${c.id}`,
        who,
        action: `Applied · ${c.posting_title || "—"}`,
        ts: c.applied_at ? new Date(c.applied_at).getTime() : new Date(c.created_at).getTime(),
        type: "req",
        entityId: c.id,
        status: c.stage_display || c.stage,
      });
    });

    onboardingProgrammes.forEach((p) => {
      /* Programme progress isn't computed by the backend — derive it from
         completed-task count out of total task count. */
      const completed = (p.tasks ?? []).filter((t) => t.status === "complete").length;
      const total = (p.tasks ?? []).length || 1;
      const percent = Math.round((completed / total) * 100);
      push({
        id: `ob-${p.id}`,
        who: p.employee_name || "Employee",
        action: `Onboarding · ${percent}% complete`,
        ts: p.start_date ? new Date(p.start_date).getTime() : new Date(p.created_at).getTime(),
        type: "ob",
        entityId: p.id,
        status: percent === 100 ? "Complete" : p.status_display || p.status,
      });
    });

    hrCases.forEach((c) => {
      push({
        id: `hc-${c.id}`,
        who: c.raised_by_name || "Employee",
        action: `Raised ${(c.priority || "normal").toLowerCase()} priority case`,
        ts: new Date(c.created_at).getTime(),
        type: "case",
        entityId: c.id,
        status: c.status_display || c.status,
      });
    });

    policies.forEach((p) => {
      push({
        id: `pol-${p.id}`,
        who: p.owner_name || "HR",
        action: `Policy '${p.title}'`,
        ts: new Date(p.created_at).getTime(),
        type: "policy",
        entityId: p.id,
        status: p.is_active ? "Active" : "Draft",
      });
    });

    let filtered = activityType === "all" ? rows : rows.filter((r) => r.type === activityType);
    filtered = [...filtered].sort((a, b) =>
      activitySort === "newest" ? b.ts - a.ts : a.ts - b.ts,
    );
    return filtered.slice(0, 12);
  }, [
    leaveRequests,
    educationClaims,
    documents,
    candidates,
    onboardingProgrammes,
    hrCases,
    policies,
    activityType,
    activitySort,
    avByName,
  ]);

  /* ----- Headcount flow (live, mode-switchable) ----- */
  const [hcMode, setHcMode] = useState<"Weekly" | "Monthly">("Weekly");

  const headcountFlow = useMemo(() => {
    const buckets = hcMode === "Weekly" ? 12 : 6;
    const bucketMs = hcMode === "Weekly" ? 7 * 86_400_000 : 30 * 86_400_000;
    const now = Date.now();

    // Audit events: joiner = create employee / hire; leaver = terminate / resign / exit.
    const joinerEvents = auditLogs
      .filter((l) => /create.*employee|hired|onboard/i.test(l.action))
      .map((l) => new Date(l.created_at).getTime());
    const leaverEvents = auditLogs
      .filter((l) => /terminate|resigned|exit|offboard/i.test(l.action))
      .map((l) => new Date(l.created_at).getTime());

    const series: Array<{ v: number; neg: number }> = [];
    const labels: string[] = [];
    for (let i = buckets - 1; i >= 0; i--) {
      const end = now - i * bucketMs;
      const start = end - bucketMs;
      const v = joinerEvents.filter((t) => t > start && t <= end).length;
      const neg = leaverEvents.filter((t) => t > start && t <= end).length;
      series.push({ v, neg });
      const d = new Date(end);
      labels.push(
        hcMode === "Weekly"
          ? d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" })
          : d.toLocaleDateString("en-GB", { month: "short" }),
      );
    }
    const labelEvery = Math.max(1, Math.floor(labels.length / 4));
    const visibleLabels = labels.filter((_, i) => i % labelEvery === 0);
    const joinersTotal = joinerEvents.filter((t) => t > now - buckets * bucketMs).length;
    const leaversTotal = leaverEvents.filter((t) => t > now - buckets * bucketMs).length;
    return { series, labels: visibleLabels, joinersTotal, leaversTotal };
  }, [auditLogs, hcMode]);

  function exportActivity() {
    downloadCsv(
      `dashboard-activity-${new Date().toISOString().slice(0, 10)}.csv`,
      recentActivity.map((r) => ({
        when: new Date(r.ts).toISOString(),
        actor: r.who,
        type: ACTIVITY_TYPE_LABEL[r.type],
        action: r.action,
        detail: r.detail,
        status: r.status,
      })),
    );
    setActivityMenuOpen(false);
  }

  return (
    <>
      <HeroCard
        eyebrow="Total workforce"
        big="131"
        delta="+4 this month"
        sub="Active across 8 departments · 6 locations"
        actions={[
          { label: "Add person", icon: <I.plus size={14} />, primary: true, onClick: () => navigate("/people") },
          { label: "Run report", icon: <I.chart size={14} />, onClick: () => navigate("/reports") },
          { label: "Send announcement", icon: <I.mail size={14} /> },
        ]}
      />

      <Card style={{ marginTop: 14 }}>
        <div style={{ padding: 18 }}>
          <div className="spread" style={{ marginBottom: 16 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--ink-3)" }}>
                Headcount flow
              </h3>
              <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 1 }}>
                Joiners and leavers over the last 30 weeks
              </div>
            </div>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <SegmentedSm
                options={["Weekly", "Monthly"]}
                value={hcMode}
                onChange={(v) => setHcMode(v as "Weekly" | "Monthly")}
              />
              <Button
                variant="outline"
                size="sm"
                leftIcon={<I.settings size={13} />}
                onClick={() => navigate("/people")}
              >
                Manage
              </Button>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 220px", gap: 24 }}>
            {headcountFlow.series.every((s) => s.v === 0 && s.neg === 0) ? (
              <div
                style={{
                  display: "grid",
                  placeItems: "center",
                  background: "var(--card-2)",
                  borderRadius: 10,
                  padding: "32px 16px",
                  minHeight: 200,
                  textAlign: "center",
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: "var(--ink-3)",
                      marginBottom: 4,
                    }}
                  >
                    No joiner / leaver events {hcMode === "Weekly" ? "in the last 12 weeks" : "in the last 6 months"}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-3)", maxWidth: 320 }}>
                    The chart populates as you add new employees from People → Add person.
                  </div>
                </div>
              </div>
            ) : (
              <BiBarChart series={headcountFlow.series} labels={headcountFlow.labels} />
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 12, justifyContent: "center" }}>
              <SideMetric
                icon={<I.arrow style={{ transform: "rotate(-45deg)" }} size={16} />}
                iconBg="var(--positive-soft)"
                iconColor="var(--positive)"
                label="Joiners"
                value={String(headcountFlow.joinersTotal)}
                delta={hcMode === "Weekly" ? "12 wk" : "6 mo"}
                deltaTone="up"
              />
              <SideMetric
                divider
                icon={<I.arrow style={{ transform: "rotate(135deg)" }} size={16} />}
                iconBg="var(--danger-soft)"
                iconColor="var(--danger)"
                label="Leavers"
                value={String(headcountFlow.leaversTotal)}
                delta={hcMode === "Weekly" ? "12 wk" : "6 mo"}
                deltaTone={headcountFlow.leaversTotal > headcountFlow.joinersTotal ? "down" : "up"}
              />
            </div>
          </div>
        </div>
      </Card>

      <KpiStrip cols={3} style={{ marginTop: 14 }}>
        <KpiCell
          icon={<I.calendar size={14} />}
          label="On leave today"
          period="Today"
          value={onLeaveToday}
          comp={`${pendingLeave.length} pending approvals`}
        />
        <KpiCell
          icon={<I.briefcase size={14} />}
          label="Open requisitions"
          period="Active"
          value={openReqs}
          comp={`${jobReqs.length} total requisitions`}
        />
        <KpiCell
          icon={<I.history size={14} />}
          label="Headcount"
          period="Now"
          value={employees.length}
          deltaTone="up"
          comp={`Across ${new Set(employees.map((e) => e.department_name)).size} departments`}
        />
      </KpiStrip>

      <div className="grid" style={{ gridTemplateColumns: "1.7fr 1fr", marginTop: 14, gap: 14 }}>
        <Card>
          <div
            style={{
              padding: "14px 18px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              borderBottom: "1px solid var(--hairline-2)",
              gap: 8,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <I.history size={14} style={{ color: "var(--text-3)" }} />
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>Recent activity</h3>
              <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>
                · live business events
              </span>
            </div>
            <div style={{ display: "flex", gap: 6, alignItems: "center", position: "relative" }}>
              <select
                value={activityType}
                onChange={(e) => setActivityType(e.target.value as typeof activityType)}
                className="select"
                style={{ height: 28, fontSize: 11.5, padding: "0 8px" }}
              >
                <option value="all">All types</option>
                {(Object.keys(ACTIVITY_TYPE_LABEL) as Array<ActivityRow["type"]>).map((t) => (
                  <option key={t} value={t}>
                    {ACTIVITY_TYPE_LABEL[t]}
                  </option>
                ))}
              </select>
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<I.list size={12} />}
                onClick={() => setActivitySort((s) => (s === "newest" ? "oldest" : "newest"))}
                title={`Sort: ${activitySort}`}
              >
                {activitySort === "newest" ? "Newest" : "Oldest"}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setActivityMenuOpen((o) => !o)}
              >
                <I.more size={14} />
              </Button>
              {activityMenuOpen && (
                <>
                  <div
                    onClick={() => setActivityMenuOpen(false)}
                    style={{ position: "fixed", inset: 0, zIndex: 30 }}
                  />
                  <div
                    className="pop"
                    style={{
                      position: "absolute",
                      top: 32,
                      right: 0,
                      width: 220,
                      background: "var(--card)",
                      border: "1px solid var(--hairline)",
                      borderRadius: 10,
                      boxShadow: "var(--shadow-pop)",
                      padding: 4,
                      zIndex: 40,
                    }}
                  >
                    <button
                      onClick={exportActivity}
                      style={{
                        width: "100%",
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 10px",
                        border: "none",
                        background: "transparent",
                        textAlign: "left",
                        fontSize: 12.5,
                        cursor: "pointer",
                        borderRadius: 6,
                      }}
                    >
                      <I.download size={13} /> Export visible as CSV
                    </button>
                    <button
                      onClick={() => {
                        setActivityType("all");
                        setActivitySort("newest");
                        setActivityMenuOpen(false);
                      }}
                      style={{
                        width: "100%",
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 10px",
                        border: "none",
                        background: "transparent",
                        textAlign: "left",
                        fontSize: 12.5,
                        cursor: "pointer",
                        borderRadius: 6,
                      }}
                    >
                      <I.refresh size={13} /> Reset filters
                    </button>
                    <button
                      onClick={() => {
                        setActivityMenuOpen(false);
                        navigate("/people");
                      }}
                      style={{
                        width: "100%",
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: "8px 10px",
                        border: "none",
                        background: "transparent",
                        textAlign: "left",
                        fontSize: 12.5,
                        cursor: "pointer",
                        borderRadius: 6,
                      }}
                    >
                      <I.users size={13} /> Open People directory
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Person</th>
                <th>Type</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>When</th>
              </tr>
            </thead>
            <tbody>
              {recentActivity.length === 0 && (
                <tr>
                  <td colSpan={4}>
                    <div
                      style={{
                        padding: 28,
                        textAlign: "center",
                        color: "var(--text-3)",
                        fontSize: 13,
                      }}
                    >
                      {activityType === "all"
                        ? "No activity yet — start using Bunchly and events will appear here."
                        : `No ${ACTIVITY_TYPE_LABEL[activityType].toLowerCase()} activity yet.`}
                    </div>
                  </td>
                </tr>
              )}
              {recentActivity.map((a) => {
                // Navigate to the right page based on the activity type.
                const linkFor: Record<ActivityRow["type"], string> = {
                  leave: "/leave",
                  claim: "/education-assistance",
                  doc: "/documents",
                  req: "/recruitment",
                  ob: "/onboarding",
                  policy: "/policies",
                  case: "/hr-cases",
                  asset: "/assets",
                  other: "/",
                };
                return (
                <tr
                  key={a.id}
                  className="clickable"
                  onClick={() => navigate(linkFor[a.type])}
                >
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <ActivityIcon
                        type={a.type === "policy" || a.type === "case" || a.type === "asset" || a.type === "other" ? "doc" : a.type}
                        bg={a.iconBg}
                        color={a.iconColor}
                      />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 12.5, color: "var(--ink-3)" }}>
                          {a.who}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-3)" }}>{a.action}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <Badge tone="outline">{ACTIVITY_TYPE_LABEL[a.type]}</Badge>
                  </td>
                  <td>
                    <span style={{ fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
                      {a.detail.split(" · ")[1] || "—"}
                    </span>
                  </td>
                  <td style={{ textAlign: "right", fontSize: 11.5, color: "var(--text-3)" }}>
                    {a.date}
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </Card>

        <div className="col" style={{ gap: 14 }}>
          <Card>
            <div style={{ padding: 18 }}>
              <div className="spread" style={{ marginBottom: 14 }}>
                <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--ink-3)" }}>
                  Your inbox
                </h3>
                <button style={{ fontSize: 11.5, color: "var(--action)", fontWeight: 500, background: "none", border: "none", cursor: "pointer" }}>
                  See all →
                </button>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <InboxRow
                  icon={<I.calendar size={14} />}
                  bg="var(--info-soft)"
                  color="var(--action)"
                  label={`${pendingLeave.length} leave requests`}
                  sub="Avg waiting: 2 days"
                  onClick={() => navigate("/leave")}
                />
                <InboxRow
                  icon={<I.money size={14} />}
                  bg="var(--yellow-soft)"
                  color="var(--yellow-deep)"
                  label={`${pendingClaims.length} education claims`}
                  sub={`$${pendingClaimsTotal.toLocaleString()} awaiting`}
                  onClick={() => navigate("/education-assistance")}
                />
                <InboxRow
                  icon={<I.document size={14} />}
                  bg="var(--positive-soft)"
                  color="var(--positive)"
                  label={`${pendingDocs.length} docs to verify`}
                  sub="Pending HR review"
                  onClick={() => navigate("/documents")}
                />
                <InboxRow
                  icon={<I.scroll size={14} />}
                  bg="var(--danger-soft)"
                  color="var(--danger)"
                  label="2 probation reviews"
                  sub="Due in 11 days"
                  onClick={() => navigate("/performance")}
                />
              </div>
            </div>
          </Card>

          <Card>
            <div style={{ padding: 18 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <I.gift size={14} style={{ color: "var(--yellow-deep)" }} />
                <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--ink-3)" }}>
                  This week
                </h3>
              </div>
              <div
                style={{
                  background: "linear-gradient(135deg, var(--yellow) 0%, #FFE07A 100%)",
                  borderRadius: 10,
                  padding: 14,
                  position: "relative",
                  overflow: "hidden",
                  marginBottom: 12,
                }}
              >
                <span className="eyebrow on-yellow-soft">Birthday today</span>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }}>
                  <Avatar name="Aiko Tanaka" av="av-1" />
                  <div>
                    <div className="on-yellow-strong" style={{ fontWeight: 600, fontSize: 13 }}>Aiko Tanaka</div>
                    <div className="on-yellow-soft" style={{ fontSize: 11.5 }}>
                      Senior Frontend Engineer · turns 31
                    </div>
                  </div>
                </div>
                <Button variant="ink" size="sm" leftIcon={<I.gift size={12} />} style={{ marginTop: 10, width: "100%" }}>
                  Send a card
                </Button>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {[
                  { name: "Pia Lindberg", what: "Birthday", when: "Sat", av: "av-2" },
                  { name: "Joseph Mensah", what: "Birthday", when: "Mon", av: "av-4" },
                  { name: "Maya Okafor", what: "7yr anniversary", when: "Fri", av: "av-1" },
                ].map((p, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0" }}>
                    <Avatar name={p.name} av={p.av} size="sm" />
                    <div style={{ flex: 1, fontSize: 12.5 }}>
                      <span style={{ fontWeight: 500 }}>{p.name}</span>
                      <span style={{ color: "var(--text-3)" }}> · {p.what}</span>
                    </div>
                    <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>{p.when}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}

/* ============================================
 * MANAGER DASHBOARD
 * ============================================ */
function ManagerDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const toast = useToast();
  const employees = useStore((s) => s.employees);
  const leaveRequests = useStore((s) => s.leaveRequests);
  const approveLeave = useStore((s) => s.approveLeave);
  const rejectLeave = useStore((s) => s.rejectLeave);

  // Show all reports where this user is line manager. Fall back to
  // Maya Okafor's team for the demo Manager seed account so the
  // dashboard isn't empty when logged in as `manager@acme.test`.
  const me = user?.full_name?.trim();
  const team =
    (me && employees.filter((e) => e.manager === me).length > 0
      ? employees.filter((e) => e.manager === me)
      : employees.filter((e) => e.manager === "Maya Okafor"));

  const pending = leaveRequests.filter(
    (r) =>
      r.status.startsWith("Pending") &&
      (r.manager === me || r.manager === "Maya Okafor"),
  );
  const approved = leaveRequests.filter(
    (r) =>
      r.status === "Approved" &&
      (r.manager === me || r.manager === "Maya Okafor"),
  );

  return (
    <>
      <HeroCard
        eyebrow="Your team"
        big={team.length.toString()}
        delta="6 active"
        sub="Engineering · 2 in probation · 0 on leave today"
        actions={[
          { label: "Review pending", icon: <I.check size={14} />, primary: true, onClick: () => navigate("/leave") },
          { label: "1:1 notes", icon: <I.message size={14} /> },
          { label: "Add goal", icon: <I.plus size={14} /> },
        ]}
      />

      <Card style={{ marginTop: 14 }}>
        <div style={{ padding: 18 }}>
          <div className="spread" style={{ marginBottom: 16 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--ink-3)" }}>
                Team activity
              </h3>
              <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 1 }}>
                Capacity, leave and approvals over time
              </div>
            </div>
            <SegmentedSm options={["Weekly", "Monthly"]} value="Weekly" />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 220px", gap: 24 }}>
            <BiBarChart
              series={Array.from({ length: 30 }, (_, i) => ({ v: (i % 5) + 1, neg: i % 7 === 0 ? 2 : 0 }))}
              labels={["18 Oct", "25 Oct", "2 Nov", "9 Nov"]}
            />
            <div style={{ display: "flex", flexDirection: "column", gap: 12, justifyContent: "center" }}>
              <SideMetric
                icon={<I.check size={16} />}
                iconBg="var(--positive-soft)"
                iconColor="var(--positive)"
                label="Approved"
                value={approved.length.toString()}
                delta="+3"
                deltaTone="up"
              />
              <SideMetric
                divider
                icon={<I.clock size={16} />}
                iconBg="var(--yellow-soft)"
                iconColor="var(--yellow-deep)"
                label="Pending"
                value={pending.length.toString()}
                delta={`${pending.length} awaiting`}
                deltaTone={pending.length > 0 ? "down" : "flat"}
              />
            </div>
          </div>
        </div>
      </Card>

      <KpiStrip cols={3} style={{ marginTop: 14 }}>
        <KpiCell
          icon={<I.calendar size={14} />}
          label="Pending approvals"
          period="Today"
          value={pending.length}
          comp={pending.length === 0 ? "All clear" : `${pending.length} awaiting your decision`}
        />
        <KpiCell
          icon={<I.check size={14} />}
          label="Approved this cycle"
          period="Lifetime"
          value={approved.length}
          deltaTone="up"
          comp="Includes everything you've approved"
        />
        <KpiCell
          icon={<I.scroll size={14} />}
          label="Probation due"
          period="Next 14 days"
          value={team.filter((e) => e.probation).length}
          deltaTone="flat"
        />
      </KpiStrip>

      <div className="grid" style={{ gridTemplateColumns: "1.7fr 1fr", marginTop: 14, gap: 14 }}>
        <Card>
          <div
            style={{
              padding: "14px 18px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              borderBottom: "1px solid var(--hairline-2)",
            }}
          >
            <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>Pending your approval</h3>
            <Button variant="ghost" size="sm">See all →</Button>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Person</th>
                <th>Type</th>
                <th>Dates</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {pending.length === 0 && (
                <tr>
                  <td colSpan={4}>
                    <div
                      style={{
                        padding: 28,
                        textAlign: "center",
                        color: "var(--text-3)",
                        fontSize: 13,
                      }}
                    >
                      All caught up — no leave requests awaiting your approval.
                    </div>
                  </td>
                </tr>
              )}
              {pending.map((r) => (
                <tr key={r.id}>
                  <td>
                    <PersonCell name={r.who} av={r.av} sub={r.reason.slice(0, 28)} />
                  </td>
                  <td>
                    <Badge
                      tone={r.type === "Annual" ? "blue" : r.type === "Sick" ? "red" : "outline"}
                    >
                      {r.type}
                    </Badge>
                  </td>
                  <td className="muted">
                    {r.days}d · {fmtDateShort(r.start)}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <div style={{ display: "inline-flex", gap: 4 }}>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          rejectLeave(r.id, me || "Manager");
                          toast.push(`${r.id} declined`, "error");
                        }}
                      >
                        Decline
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => {
                          approveLeave(r.id, me || "Manager");
                          toast.push(`${r.id} approved — ${r.who} notified`, "success");
                        }}
                      >
                        Approve
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card>
          <div style={{ padding: 18 }}>
            <div className="spread" style={{ marginBottom: 14 }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>Your team</h3>
              <Button variant="ghost" size="sm" onClick={() => navigate("/people")}>View →</Button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {team.slice(0, 6).map((p) => (
                <div
                  key={p.id}
                  onClick={() => navigate(`/people/${p.id}`)}
                  style={{
                    display: "flex",
                    gap: 10,
                    alignItems: "center",
                    padding: "6px 0",
                    cursor: "pointer",
                    borderBottom: "1px solid var(--hairline-2)",
                  }}
                >
                  <Avatar name={p.name} av={p.av} size="sm" />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 500 }}>{p.name}</div>
                    <div style={{ fontSize: 11, color: "var(--text-3)" }}>{p.title}</div>
                  </div>
                  <StatusBadge status={p.status} />
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}

/* ============================================
 * EMPLOYEE DASHBOARD
 * ============================================ */
function EmployeeDashboard() {
  const navigate = useNavigate();

  const balances = [
    { name: "Annual", used: 8, total: 21, color: "var(--action)" },
    { name: "Sick", used: 1, total: 10, color: "var(--danger)" },
    { name: "Study", used: 0, total: 5, color: "var(--bunchly)" },
    { name: "Compassionate", used: 0, total: 5, color: "#7B5BFF" },
  ];

  const cellStyle: CSSProperties = { fontWeight: 500, fontSize: 12.5 };

  return (
    <>
      <HeroCard
        eyebrow="My leave balance"
        big="13"
        delta="days"
        sub="of 21 annual days · refreshes 1 Mar 2027"
        actions={[
          { label: "Request leave", icon: <I.plus size={14} />, primary: true, onClick: () => navigate("/leave") },
          { label: "Upload document", icon: <I.upload size={14} />, onClick: () => navigate("/documents") },
          { label: "Submit claim", icon: <I.money size={14} />, onClick: () => navigate("/education-assistance") },
        ]}
      />

      <KpiStrip cols={4} style={{ marginTop: 14 }}>
        {balances.map((t) => (
          <KpiCell
            key={t.name}
            label={`${t.name} leave`}
            value={(t.total - t.used).toString()}
            valueSuffix={`/ ${t.total} days`}
            meter={<Meter value={t.used} max={t.total} color={t.color} thin />}
            sub={`${t.used} used · ${t.total - t.used} remaining`}
          />
        ))}
      </KpiStrip>

      <div className="grid" style={{ gridTemplateColumns: "1.5fr 1fr", marginTop: 14, gap: 14 }}>
        <Card>
          <div
            style={{
              padding: "14px 18px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              borderBottom: "1px solid var(--hairline-2)",
            }}
          >
            <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>My requests</h3>
            <Button variant="ghost" size="sm" onClick={() => navigate("/leave")}>See all →</Button>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Detail</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <ActivityIcon type="leave" bg="var(--info-soft)" color="var(--action)" />
                    <div>
                      <div style={cellStyle}>Annual leave</div>
                      <div style={{ fontSize: 11, color: "var(--text-3)" }}>Submitted May 15</div>
                    </div>
                  </div>
                </td>
                <td>
                  <div style={cellStyle}>7 days</div>
                  <div style={{ fontSize: 11, color: "var(--text-3)" }}>Jul 12 – Jul 20</div>
                </td>
                <td>
                  <Badge tone="yellow" dot>Awaiting Farai</Badge>
                </td>
              </tr>
              <tr>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <ActivityIcon type="claim" bg="var(--yellow-soft)" color="var(--yellow-deep)" />
                    <div>
                      <div style={cellStyle}>Home office stipend</div>
                      <div style={{ fontSize: 11, color: "var(--text-3)" }}>Submitted May 14</div>
                    </div>
                  </div>
                </td>
                <td>
                  <div style={cellStyle}>$400</div>
                  <div style={{ fontSize: 11, color: "var(--text-3)" }}>3 receipts attached</div>
                </td>
                <td>
                  <Badge tone="blue" dot>HR review</Badge>
                </td>
              </tr>
              <tr>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <ActivityIcon type="doc" bg="var(--positive-soft)" color="var(--positive)" />
                    <div>
                      <div style={cellStyle}>Tax certificate</div>
                      <div style={{ fontSize: 11, color: "var(--text-3)" }}>Uploaded Feb 28</div>
                    </div>
                  </div>
                </td>
                <td>
                  <div style={cellStyle}>342 KB</div>
                  <div style={{ fontSize: 11, color: "var(--text-3)" }}>Verified by Olamide</div>
                </td>
                <td>
                  <Badge tone="green" dot>Done</Badge>
                </td>
              </tr>
            </tbody>
          </table>
        </Card>

        <Card>
          <div style={{ padding: 18 }}>
            <div className="spread" style={{ marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>Latest payslip</h3>
              <Button variant="ghost" size="sm" leftIcon={<I.download size={12} />}>PDF</Button>
            </div>
            <div
              style={{
                background:
                  "linear-gradient(135deg, var(--action) 0%, var(--action-deep) 100%)",
                color: "#fff",
                padding: 16,
                borderRadius: 12,
                position: "relative",
                overflow: "hidden",
              }}
            >
              <div style={{ fontSize: 11, opacity: 0.7 }}>April 2026 · paid 29 Apr</div>
              <div
                style={{
                  fontSize: 26,
                  fontWeight: 600,
                  marginTop: 6,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                $4,860.42
              </div>
              <div style={{ fontSize: 11, opacity: 0.7, marginTop: 2 }}>Net pay · USD</div>
              <div
                style={{
                  marginTop: 14,
                  paddingTop: 10,
                  borderTop: "1px solid rgba(255,255,255,0.18)",
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 11.5,
                }}
              >
                <span style={{ opacity: 0.7 }}>Gross</span>
                <span style={{ fontWeight: 500 }}>$6,210.00</span>
              </div>
              <div
                style={{
                  marginTop: 4,
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 11.5,
                }}
              >
                <span style={{ opacity: 0.7 }}>Tax & deductions</span>
                <span style={{ fontWeight: 500 }}>−$1,349.58</span>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}

/* Unused but exported helper for typing — prevents unused-import warnings
   while keeping the IconName type accessible to other dashboard variants. */
export type _IconName = IconName;
