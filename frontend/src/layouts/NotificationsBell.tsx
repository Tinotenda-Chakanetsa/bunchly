/* Top-bar notifications bell + dropdown.

   - Unread count polled every 30s so cross-tab activity surfaces.
   - Clicking a notification marks it read and (if it has a `url`)
     navigates to the related record.
   - "Mark all read" is a single bulk endpoint call.

   Backend endpoints (apps/notifications):
     GET    /notifications/                  list (paginated)
     GET    /notifications/unread-count/     { unread: N }
     POST   /notifications/:id/mark-read/    mark one
     POST   /notifications/mark-all-read/    mark all
*/
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  unreadNotificationCount,
  type NotificationRecord,
} from "@/api/notifications";

function timeAgo(iso: string): string {
  const t = new Date(iso).getTime();
  const diff = Math.max(0, Date.now() - t);
  const s = Math.floor(diff / 1000);
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

function levelColor(level: NotificationRecord["level"]) {
  if (level === "error") return "var(--negative)";
  if (level === "warning") return "var(--yellow)";
  if (level === "success") return "var(--positive)";
  return "var(--action)";
}

/* Notification → in-app route resolver.
 *
 * Most backend dispatch() calls populate `entity_type` + `entity_id` but
 * leave `url` blank. Rather than plumbing a URL through every domain
 * service (and having frontend route names leak into the backend), we
 * derive the destination from those fields here. If a backend later sets
 * `url` explicitly that wins.
 *
 * Entries with no per-id detail page (payroll payslips, attendance
 * records, education claims) drop to the list view, which is the
 * page that surfaces the inbox/queue for that domain.
 */
const ENTITY_ROUTES: Record<string, (id: string) => string> = {
  "leave.leave_request": (id) => `/leave/${id}`,
  "leave.balance": () => "/leave",
  "education_assistance.claim": () => "/education-assistance",
  "documents.document": (id) => `/documents/${id}`,
  "documents.category": () => "/documents",
  /* Employee-facing — every payslip recipient can land here regardless
     of payroll permissions. The payroll managers' view lives at /payroll. */
  "payroll.payslip": () => "/my-payslips",
  "payroll.period": (id) => `/payroll/${id}`,
  "policies.policy": () => "/policies",
  "policies.assignment": () => "/policies",
  "attendance.record": () => "/attendance",
  "helpdesk.case": (id) => `/hr-cases/${id}`,
  "recruitment.candidate": (id) => `/recruitment/${id}`,
  "recruitment.requisition": () => "/recruitment",
  "onboarding.programme": (id) => `/onboarding/${id}`,
  "onboarding.task": () => "/onboarding",
  "performance.review": (id) => `/performance/${id}`,
  "performance.cycle": () => "/performance",
  "employees.employee": (id) => `/people/${id}`,
  "benefits.enrolment": () => "/benefits",
  "benefits.benefittype": () => "/benefits",
  "learning.training_record": () => "/learning",
  "imports.import_batch": () => "/imports",
  "workflows.workflow_instance": () => "/", // no first-class route yet
};

function resolveUrl(n: NotificationRecord): string | null {
  if (n.url) return n.url;
  if (!n.entity_type) return null;
  const builder = ENTITY_ROUTES[n.entity_type];
  if (!builder) return null;
  return builder(n.entity_id || "");
}

export default function NotificationsBell() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const popRef = useRef<HTMLDivElement | null>(null);

  // Unread badge — polled in the background.
  const unread = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: unreadNotificationCount,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  });

  // List only fetched when the popover is opened.
  const list = useQuery({
    queryKey: ["notifications", "list"],
    queryFn: () => listNotifications(),
    enabled: open,
  });

  const markOne = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications", "list"] });
      queryClient.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
    },
  });
  const markAll = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications", "list"] });
      queryClient.invalidateQueries({ queryKey: ["notifications", "unread-count"] });
    },
  });

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (popRef.current && !popRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const items = list.data?.results ?? [];
  const unreadCount = unread.data ?? 0;

  function activate(n: NotificationRecord) {
    if (!n.is_read) markOne.mutate(n.id);
    setOpen(false);
    const dest = resolveUrl(n);
    if (dest) navigate(dest);
  }

  return (
    <div style={{ position: "relative" }} ref={popRef}>
      <button
        className="icon-btn"
        title="Notifications"
        onClick={() => setOpen((o) => !o)}
      >
        <I.bell size={16} />
        {unreadCount > 0 && (
          <span
            className="dot"
            style={{
              background: "var(--yellow)",
              minWidth: 7,
              height: 7,
              borderRadius: 999,
            }}
          />
        )}
      </button>
      {open && (
        <div
          className="pop"
          style={{
            position: "absolute",
            top: 42,
            right: 0,
            width: 360,
            maxHeight: 520,
            background: "var(--card)",
            border: "1px solid var(--hairline)",
            borderRadius: 12,
            boxShadow: "var(--shadow-pop)",
            zIndex: 40,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "12px 14px",
              borderBottom: "1px solid var(--hairline-2)",
            }}
          >
            <div style={{ fontWeight: 600, fontSize: 13, color: "var(--ink-3)", flex: 1 }}>
              Notifications
              {unreadCount > 0 && (
                <span
                  style={{
                    marginLeft: 8,
                    fontSize: 11,
                    background: "var(--yellow-soft)",
                    color: "var(--yellow-deep)",
                    padding: "1px 8px",
                    borderRadius: 999,
                    fontWeight: 600,
                  }}
                >
                  {unreadCount} new
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={() => markAll.mutate()}
                disabled={markAll.isPending}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--action)",
                  fontSize: 12,
                  cursor: "pointer",
                  fontWeight: 500,
                }}
              >
                {markAll.isPending ? "Marking…" : "Mark all read"}
              </button>
            )}
          </div>
          <div style={{ overflowY: "auto", flex: 1 }}>
            {list.isLoading ? (
              <div style={{ padding: 24, color: "var(--text-3)", fontSize: 13 }}>
                Loading…
              </div>
            ) : items.length === 0 ? (
              <div style={{ padding: "28px 18px", textAlign: "center" }}>
                <I.bell size={24} style={{ color: "var(--text-4)" }} />
                <div
                  style={{
                    fontSize: 13,
                    color: "var(--text-2)",
                    fontWeight: 500,
                    marginTop: 8,
                  }}
                >
                  You're all caught up
                </div>
                <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2 }}>
                  Activity that involves you will show here.
                </div>
              </div>
            ) : (
              items.map((n) => {
                const dest = resolveUrl(n);
                return (
                  <button
                    key={n.id}
                    type="button"
                    onClick={() => activate(n)}
                    title={dest ? `Open ${dest}` : "Mark as read"}
                    style={{
                      display: "flex",
                      gap: 10,
                      width: "100%",
                      background: n.is_read ? "transparent" : "var(--info-soft)",
                      border: "none",
                      borderBottom: "1px solid var(--hairline-2)",
                      padding: "12px 14px",
                      textAlign: "left",
                      cursor: "pointer",
                      transition: "background 0.1s",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background = "var(--mist)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = n.is_read
                        ? "transparent"
                        : "var(--info-soft)")
                    }
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 999,
                        background: n.is_read ? "var(--hairline)" : levelColor(n.level),
                        marginTop: 5,
                        flexShrink: 0,
                      }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: n.is_read ? 400 : 600,
                          color: "var(--ink-3)",
                          marginBottom: 2,
                        }}
                      >
                        {n.title}
                      </div>
                      {n.body && (
                        <div
                          style={{
                            fontSize: 12,
                            color: "var(--text-2)",
                            marginBottom: 4,
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {n.body}
                        </div>
                      )}
                      <div style={{ fontSize: 11, color: "var(--text-3)" }}>
                        {timeAgo(n.created_at)}
                      </div>
                    </div>
                    {dest && (
                      <I.chevron
                        size={14}
                        style={{
                          color: "var(--text-3)",
                          marginTop: 4,
                          flexShrink: 0,
                        }}
                      />
                    )}
                  </button>
                );
              })
            )}
          </div>
          {items.length > 0 && (
            <div
              style={{
                padding: "10px 14px",
                borderTop: "1px solid var(--hairline-2)",
                textAlign: "center",
                background: "var(--card-2)",
              }}
            >
              <span
                style={{ fontSize: 11.5, color: "var(--text-3)" }}
              >
                Showing latest {items.length}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
