import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardHead,
  KpiCell,
  KpiStrip,
  Modal,
  PageHeader,
  Pagination,
  PersonCell,
  Stars,
  StatusBadge,
  Tabs,
  useToast,
  usePaginated,
} from "@/components/ui";
import { downloadCsv } from "@/lib/export";
import { useAuth } from "@/store/auth";
import { listEmployees } from "@/api/employees";
import {
  acknowledgePerformanceReview,
  completePerformanceReview,
  listPerformanceReviews,
  listReviewCycles,
  startPerformanceReview,
  submitPerformanceReview,
  updatePerformanceReview,
  type PerformanceReview,
} from "@/api/hr";

function StartReviewModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const employees = useQuery({
    queryKey: ["employees", "for-perf"],
    queryFn: () => listEmployees(),
    enabled: open,
  });
  const cycles = useQuery({
    queryKey: ["review-cycles"],
    queryFn: listReviewCycles,
    enabled: open,
  });
  const [employee, setEmployee] = useState("");
  const [cycle, setCycle] = useState("");
  const [dueDate, setDueDate] = useState(
    new Date(Date.now() + 14 * 86_400_000).toISOString().slice(0, 10),
  );

  const start = useMutation({
    mutationFn: startPerformanceReview,
    onSuccess: () => {
      toast.push("Review started", "success");
      queryClient.invalidateQueries({ queryKey: ["performance-reviews"] });
      onClose();
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not start review",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!employee || !cycle) {
      toast.push("Pick an employee and a cycle", "error");
      return;
    }
    start.mutate({ employee, cycle, due_date: dueDate });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Start performance review"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={start.isPending}>
            {start.isPending ? "Starting…" : "Start review"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="grid grid-2" style={{ gap: 14 }}>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Employee</label>
            <select
              className="select"
              value={employee}
              onChange={(e) => setEmployee(e.target.value)}
            >
              <option value="">{employees.isLoading ? "Loading…" : "Pick an employee"}</option>
              {(employees.data?.results ?? []).map((e) => (
                <option key={e.id} value={e.id}>
                  {e.full_name || `${e.first_name} ${e.last_name}`}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Cycle</label>
            <select className="select" value={cycle} onChange={(e) => setCycle(e.target.value)}>
              <option value="">{cycles.isLoading ? "Loading…" : "Pick a cycle"}</option>
              {(cycles.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Due date</label>
            <input
              className="input"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>
        </div>
      </form>
    </Modal>
  );
}

export default function PerformancePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { hasPerm } = useAuth();
  const canManage = hasPerm("performance.manage");
  const canReview = hasPerm("performance.review") || canManage;
  const [tab, setTab] = useState("cycle");
  const [showStart, setShowStart] = useState(false);

  const reviews = useQuery({
    queryKey: ["performance-reviews"],
    queryFn: () => listPerformanceReviews(),
  });

  const advance = useMutation({
    mutationFn: (vars: { id: string; action: "submit" | "acknowledge" | "complete" }) => {
      if (vars.action === "submit") return submitPerformanceReview(vars.id);
      if (vars.action === "acknowledge") return acknowledgePerformanceReview(vars.id);
      return completePerformanceReview(vars.id);
    },
    onSuccess: () => {
      toast.push("Stage updated", "success");
      queryClient.invalidateQueries({ queryKey: ["performance-reviews"] });
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not advance review",
        "error",
      ),
  });

  function nextActions(status: string): Array<{ value: "submit" | "acknowledge" | "complete"; label: string }> {
    if (status === "draft") return [{ value: "submit", label: "Submit" }];
    if (status === "submitted") return [{ value: "acknowledge", label: "Acknowledge" }];
    if (status === "acknowledged") return [{ value: "complete", label: "Complete" }];
    return [];
  }

  const rows = reviews.data?.results ?? [];
  const pag = usePaginated(rows);
  const completeCount = rows.filter((r) => r.status === "completed").length;
  const inFlight = rows.length - completeCount;
  const ratings = rows.filter((r) => r.overall_rating != null);
  const avg =
    ratings.length === 0
      ? "—"
      : (
          ratings.reduce((a, r) => a + Number(r.overall_rating || 0), 0) /
          ratings.length
        ).toFixed(1);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Growth & feedback"
        title="Performance"
        lede={reviews.isLoading ? "Loading…" : `${rows.length} reviews · ${completeCount} complete`}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={() => downloadCsv("performance-reviews.csv", rows)}
            >
              Export
            </Button>
            {canManage && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.plus size={14} />}
                onClick={() => setShowStart(true)}
              >
                Start review
              </Button>
            )}
          </>
        }
      />
      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="In flight" value={inFlight} />
        <KpiCell label="Complete" value={completeCount} />
        <KpiCell label="Avg rating" value={avg} />
        <KpiCell label="Draft" value={rows.filter((r) => r.status === "draft").length} />
      </KpiStrip>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[{ value: "cycle", label: "Current cycle", count: rows.length }]}
      />
      {tab === "cycle" && (
        <Card>
          <table className="table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Cycle</th>
                <th>Rating</th>
                <th>Status</th>
                <th>Reviewer</th>
                <th>Due</th>
                <th>Move stage</th>
              </tr>
            </thead>
            <tbody>
              {pag.slice.map((r) => (
                <tr
                  key={r.id}
                  className="clickable"
                  onClick={() => navigate(`/performance/${r.id}`)}
                >
                  <td>
                    <PersonCell name={r.employee_name || "—"} />
                  </td>
                  <td>
                    <Badge tone="blue">{r.cycle_name || "—"}</Badge>
                  </td>
                  <td>
                    <Stars value={r.overall_rating != null ? Number(r.overall_rating) : null} />
                  </td>
                  <td>
                    <StatusBadge status={r.status_display || r.status} />
                  </td>
                  <td className="muted">{r.reviewer_name || "—"}</td>
                  <td className="muted num">{r.due_date || "—"}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    {!canReview || nextActions(r.status).length === 0 ? (
                      <span className="muted" style={{ fontSize: 11.5 }}>—</span>
                    ) : (
                      <select
                        className="select"
                        value=""
                        onChange={(e) =>
                          e.target.value &&
                          advance.mutate({
                            id: r.id,
                            action: e.target.value as "submit" | "acknowledge" | "complete",
                          })
                        }
                        disabled={advance.isPending}
                        style={{ height: 28, fontSize: 11.5 }}
                      >
                        <option value="">Move to…</option>
                        {nextActions(r.status).map((a) => (
                          <option key={a.value} value={a.value}>
                            {a.label}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && reviews.isFetched && (
                <tr>
                  <td colSpan={7}>
                    <div style={{ padding: 28, color: "var(--text-3)", textAlign: "center" }}>
                      No reviews yet.
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <Pagination
            page={pag.page}
            pages={pag.pages}
            pageSize={pag.pageSize}
            total={pag.total}
            setPage={pag.setPage}
          />
        </Card>
      )}
      <StartReviewModal open={showStart} onClose={() => setShowStart(false)} />
    </div>
  );
}

export function ReviewDetailPage() {
  const navigate = useNavigate();
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { hasPerm } = useAuth();
  const canReview = hasPerm("performance.review") || hasPerm("performance.manage");

  const reviews = useQuery({
    queryKey: ["performance-reviews", "for-detail"],
    queryFn: () => listPerformanceReviews(),
  });
  const r = (reviews.data?.results ?? []).find((x) => x.id === id);

  const [draftRating, setDraftRating] = useState<number>(
    r?.overall_rating ? Number(r.overall_rating) : 3,
  );

  const saveRating = useMutation({
    mutationFn: () => updatePerformanceReview(id, { overall_rating: String(draftRating) }),
    onSuccess: () => {
      toast.push("Rating saved", "success");
      queryClient.invalidateQueries({ queryKey: ["performance-reviews"] });
    },
  });

  if (reviews.isLoading) {
    return (
      <div className="page">
        <div style={{ padding: 40, color: "var(--text-3)" }}>Loading…</div>
      </div>
    );
  }
  if (!r) {
    return (
      <div className="page">
        <Button variant="ghost" size="sm" onClick={() => navigate("/performance")}>← Back</Button>
        <div className="empty">
          <div className="title">Review not found</div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <Button
        variant="ghost"
        size="sm"
        style={{ marginBottom: 16 }}
        onClick={() => navigate("/performance")}
      >
        <I.chevron size={14} style={{ transform: "rotate(180deg)" }} /> Back to Performance
      </Button>
      <Card>
        <div style={{ padding: 28 }}>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <Avatar name={r.employee_name || "?"} size="xl" />
            <div style={{ flex: 1 }}>
              <span className="eyebrow">{r.cycle_name}</span>
              <h1 style={{ fontSize: 32, color: "var(--ink-3)", margin: "6px 0" }}>
                {r.employee_name}'s performance review
              </h1>
              <div style={{ color: "var(--text-2)" }}>
                Reviewer · {r.reviewer_name || "—"} · Due {r.due_date || "—"}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <Stars value={r.overall_rating ? Number(r.overall_rating) : null} />
              <div style={{ fontSize: 36, color: "var(--ink-3)", marginTop: 4 }}>
                {r.overall_rating ?? "—"}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {canReview && (
        <Card style={{ marginTop: 20 }}>
          <CardHead title="Set rating" />
          <div className="card-body">
            <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
              <input
                type="range"
                min={1}
                max={5}
                step={0.1}
                value={draftRating}
                onChange={(e) => setDraftRating(Number(e.target.value))}
                style={{ flex: 1 }}
              />
              <div style={{ fontSize: 28, color: "var(--ink-3)", minWidth: 60 }}>
                {draftRating.toFixed(1)}
              </div>
            </div>
            <Button
              variant="primary"
              size="sm"
              style={{ marginTop: 16 }}
              disabled={saveRating.isPending}
              onClick={() => saveRating.mutate()}
            >
              {saveRating.isPending ? "Saving…" : "Save rating"}
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
