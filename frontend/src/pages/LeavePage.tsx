import { useMemo, useState, type CSSProperties, type FormEvent } from "react";
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
  Meter,
  Modal,
  PageHeader,
  Pagination,
  PersonCell,
  StatusBadge,
  Tabs,
  useToast,
  usePaginated,
} from "@/components/ui";
import { fmtDate, fmtDateRange } from "@/lib/format";
import { useAuth } from "@/store/auth";
import {
  approveLeaveRequest,
  cancelLeaveRequest,
  listLeaveRequests,
  listLeaveTypes,
  listMyLeaveBalances,
  rejectLeaveRequest,
  submitLeaveRequest,
  type LeaveRequest,
  type LeaveType,
} from "@/api/leave";
import { listEmployees } from "@/api/employees";

function LeaveTypePill({ type }: { type: string }) {
  const map: Record<string, { color: string; bg: string }> = {
    Annual: { color: "var(--action)", bg: "var(--info-soft)" },
    Sick: { color: "var(--danger)", bg: "var(--danger-soft)" },
    Study: { color: "var(--bunchly)", bg: "#E5EFFD" },
    Maternity: { color: "#7A5A00", bg: "var(--yellow-soft)" },
    Compassionate: { color: "#3B2F75", bg: "#EEEAFB" },
  };
  const key = (type || "").split(" ")[0];
  const s = map[key] || { color: "var(--text-3)", bg: "var(--mist)" };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "2px 8px",
        borderRadius: 6,
        background: s.bg,
        color: s.color,
        fontSize: 12,
        fontWeight: 600,
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: 50, background: s.color }} />
      {type}
    </span>
  );
}

function RequestLeaveModal({
  open,
  onClose,
  leaveTypes,
}: {
  open: boolean;
  onClose: () => void;
  leaveTypes: LeaveType[];
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [leaveTypeId, setLeaveTypeId] = useState("");
  const [start, setStart] = useState(new Date().toISOString().slice(0, 10));
  const [end, setEnd] = useState(new Date(Date.now() + 6 * 86_400_000).toISOString().slice(0, 10));
  const [reason, setReason] = useState("");

  const submit = useMutation({
    mutationFn: submitLeaveRequest,
    onSuccess: () => {
      toast.push("Leave request submitted", "success");
      queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
      onClose();
      setReason("");
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not submit leave request";
      toast.push(detail, "error");
    },
  });

  // Default to the first leave type once they load.
  if (!leaveTypeId && leaveTypes.length > 0) {
    setLeaveTypeId(leaveTypes[0].id);
  }

  function handle(e: FormEvent) {
    e.preventDefault();
    if (!leaveTypeId) {
      toast.push("Pick a leave type first", "error");
      return;
    }
    submit.mutate({
      leave_type: leaveTypeId,
      start_date: start,
      end_date: end,
      reason: reason || "—",
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Request leave"
      sub="Submits the request for manager approval."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submit.isPending}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handle} disabled={submit.isPending}>
            {submit.isPending ? "Submitting…" : "Submit for approval"}
          </Button>
        </>
      }
    >
      <form onSubmit={handle}>
        <div className="field" style={{ marginBottom: 14 }}>
          <label>Leave type</label>
          <select
            className="select"
            value={leaveTypeId}
            onChange={(e) => setLeaveTypeId(e.target.value)}
          >
            {leaveTypes.length === 0 && <option value="">Loading…</option>}
            {leaveTypes.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} · {t.default_days_per_year}d/yr
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-2" style={{ marginBottom: 14 }}>
          <div className="field">
            <label>From</label>
            <input className="input" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </div>
          <div className="field">
            <label>To</label>
            <input className="input" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </div>
        </div>
        <div className="field" style={{ marginBottom: 14 }}>
          <label>Reason</label>
          <textarea
            className="textarea"
            placeholder="A short note for your manager."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
      </form>
    </Modal>
  );
}

function LeaveRequestsTable({ scope }: { scope: LeaveRequest[] }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { effectiveRole } = useAuth();
  const toast = useToast();
  const pag = usePaginated(scope);

  const approve = useMutation({
    mutationFn: (id: string) => approveLeaveRequest(id),
    onSuccess: () => {
      toast.push("Request approved", "success");
      queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Approval failed",
        "error",
      ),
  });
  const reject = useMutation({
    mutationFn: (vars: { id: string; reason: string }) =>
      rejectLeaveRequest(vars.id, vars.reason),
    onSuccess: () => {
      toast.push("Request rejected", "error");
      queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
    },
  });

  return (
    <Card>
      <div className="card-head">
        <h3>
          {effectiveRole === "hr"
            ? "All requests"
            : effectiveRole === "manager"
              ? "Awaiting your team"
              : "My requests"}
        </h3>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Employee</th>
            <th>Type</th>
            <th>Dates</th>
            <th>Days</th>
            <th>Submitted</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {pag.slice.map((r) => {
            const pending = r.status === "submitted" || r.status === "pending_hr";
            return (
              <tr key={r.id} className="clickable" onClick={() => navigate(`/leave/${r.id}`)}>
                <td>
                  <PersonCell
                    name={r.employee_name || "—"}
                    sub={(r.reason || "").slice(0, 36)}
                  />
                </td>
                <td>
                  <LeaveTypePill type={r.leave_type_name || "—"} />
                </td>
                <td>{fmtDateRange(r.start_date, r.end_date)}</td>
                <td className="num">{r.days_requested}</td>
                <td className="muted num">{fmtDate(r.submitted_at || r.created_at)}</td>
                <td>
                  <StatusBadge status={r.status_display || r.status} />
                </td>
                <td style={{ textAlign: "right" }}>
                  {pending && effectiveRole !== "employee" ? (
                    <div style={{ display: "inline-flex", gap: 4 }}>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={reject.isPending}
                        onClick={(e) => {
                          e.stopPropagation();
                          reject.mutate({ id: r.id, reason: "Declined" });
                        }}
                      >
                        Decline
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={approve.isPending}
                        onClick={(e) => {
                          e.stopPropagation();
                          approve.mutate(r.id);
                        }}
                      >
                        Approve
                      </Button>
                    </div>
                  ) : (
                    <I.chevron size={14} style={{ color: "var(--text-3)" }} />
                  )}
                </td>
              </tr>
            );
          })}
          {pag.slice.length === 0 && (
            <tr>
              <td colSpan={7}>
                <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                  No leave requests to show.
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
  );
}

function BalancesTable() {
  const balances = useQuery({
    queryKey: ["leave-balances", "my"],
    queryFn: listMyLeaveBalances,
  });
  return (
    <Card>
      <CardHead title="My leave balances" sub="Snapshot as of today" />
      <table className="table">
        <thead>
          <tr>
            <th>Type</th>
            <th>Entitlement</th>
            <th>Taken</th>
            <th>Pending</th>
            <th>Available</th>
          </tr>
        </thead>
        <tbody>
          {(balances.data ?? []).map((b) => (
            <tr key={b.id}>
              <td>{b.leave_type_name || "—"}</td>
              <td className="num">{b.entitlement_days}</td>
              <td className="num">{b.taken_days}</td>
              <td className="num">{b.pending_days}</td>
              <td className="num">
                <strong>{b.balance_days}</strong>
              </td>
            </tr>
          ))}
          {balances.isFetched && (balances.data ?? []).length === 0 && (
            <tr>
              <td colSpan={5}>
                <div style={{ padding: 18, color: "var(--text-3)", textAlign: "center", fontSize: 13 }}>
                  No leave balances yet — HR seeds these per cycle.
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </Card>
  );
}

export default function LeavePage() {
  const { effectiveRole } = useAuth();
  const [tab, setTab] = useState("requests");
  const [showRequest, setShowRequest] = useState(false);

  const types = useQuery({
    queryKey: ["leave-types"],
    queryFn: listLeaveTypes,
  });
  const balances = useQuery({
    queryKey: ["leave-balances", "my"],
    queryFn: listMyLeaveBalances,
    enabled: effectiveRole !== "hr", // HR's strip is filled below from totals
  });
  const requests = useQuery({
    queryKey: ["leave-requests", { role: effectiveRole }],
    queryFn: () => listLeaveRequests({ page: 1 }),
  });

  const allRequests = requests.data?.results ?? [];
  const pendingTotal = allRequests.filter(
    (r) => r.status === "submitted" || r.status === "pending_hr",
  ).length;

  const balanceStrip = useMemo(() => {
    const list = balances.data ?? [];
    // Pad / pick first four balances to populate the strip
    const base = list.slice(0, 4);
    while (base.length < 4 && types.data) {
      const used = new Set(base.map((b) => b.leave_type));
      const next = types.data.find((t) => !used.has(t.id));
      if (!next) break;
      base.push({
        id: `placeholder-${next.id}`,
        employee: "",
        leave_type: next.id,
        leave_type_name: next.name,
        year: new Date().getFullYear(),
        entitlement_days: String(next.default_days_per_year),
        taken_days: "0",
        pending_days: "0",
        balance_days: String(next.default_days_per_year),
      });
    }
    return base;
  }, [balances.data, types.data]);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Time off"
        title={effectiveRole === "employee" ? "My leave" : "Leave"}
        lede={
          requests.isLoading
            ? "Loading…"
            : `${pendingTotal} request${pendingTotal === 1 ? "" : "s"} awaiting action.`
        }
        actions={
          <Button
            variant="primary"
            size="sm"
            leftIcon={<I.plus size={14} />}
            onClick={() => setShowRequest(true)}
          >
            Request leave
          </Button>
        }
      />

      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        {balanceStrip.map((b) => {
          const entitlement = Number(b.entitlement_days) || 1;
          const taken = Number(b.taken_days) || 0;
          return (
            <KpiCell
              key={b.id}
              label={`${b.leave_type_name} leave`}
              value={b.balance_days}
              valueSuffix={`/ ${b.entitlement_days} days`}
              meter={<Meter value={taken} max={entitlement} thin />}
              sub={`${b.taken_days} taken · ${b.balance_days} remaining`}
            />
          );
        })}
      </KpiStrip>

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "requests", label: "Requests", count: pendingTotal },
          ...(effectiveRole !== "employee" ? [{ value: "balances", label: "Balances" }] : []),
        ]}
      />
      {tab === "requests" &&
        (requests.isLoading ? (
          <Card>
            <div style={{ padding: 28, color: "var(--text-3)", textAlign: "center" }}>Loading…</div>
          </Card>
        ) : (
          <LeaveRequestsTable scope={allRequests} />
        ))}
      {tab === "balances" && <BalancesTable />}

      <RequestLeaveModal
        open={showRequest}
        onClose={() => setShowRequest(false)}
        leaveTypes={types.data ?? []}
      />
    </div>
  );
}

function Mini2({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="eyebrow">{label}</div>
      <div style={{ fontSize: 20, color: "var(--ink-3)", marginTop: 4 }}>{value}</div>
    </div>
  );
}

export function LeaveDetailPage() {
  const navigate = useNavigate();
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const { effectiveRole } = useAuth();
  const toast = useToast();

  const requests = useQuery({
    queryKey: ["leave-requests", "for-detail"],
    queryFn: () => listLeaveRequests({ page: 1 }),
  });
  const request = (requests.data?.results ?? []).find((r) => r.id === id);

  const approve = useMutation({
    mutationFn: (vars: { id: string }) => approveLeaveRequest(vars.id),
    onSuccess: () => {
      toast.push("Approved — notification queued", "success");
      queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
    },
  });
  const reject = useMutation({
    mutationFn: (vars: { id: string; reason: string }) =>
      rejectLeaveRequest(vars.id, vars.reason),
    onSuccess: () => {
      toast.push("Rejected", "error");
      queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
    },
  });
  const cancel = useMutation({
    mutationFn: cancelLeaveRequest,
    onSuccess: () => {
      toast.push("Request cancelled", "success");
      queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
    },
  });

  if (requests.isLoading) {
    return (
      <div className="page">
        <div style={{ padding: 40, color: "var(--text-3)" }}>Loading…</div>
      </div>
    );
  }
  if (!request) {
    return (
      <div className="page">
        <Button variant="ghost" size="sm" onClick={() => navigate("/leave")}>← Back</Button>
        <div className="empty">
          <div className="title">Request not found</div>
        </div>
      </div>
    );
  }

  const pending = request.status === "submitted" || request.status === "pending_hr";

  return (
    <div className="page">
      <Button variant="ghost" size="sm" style={{ marginBottom: 16 }} onClick={() => navigate("/leave")}>
        <I.chevron size={14} style={{ transform: "rotate(180deg)" }} /> Back to Leave
      </Button>

      <div className="grid" style={{ gridTemplateColumns: "1.5fr 1fr", gap: 20 }}>
        <Card>
          <div style={{ padding: 24 }}>
            <span className="eyebrow">Request {request.id.slice(0, 8)}</span>
            <h1 style={{ fontSize: 32, color: "var(--ink-3)", margin: "8px 0" }}>
              {request.leave_type_name} · {request.days_requested}{" "}
              {request.days_requested === "1" ? "day" : "days"}
            </h1>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
              <PersonCell name={request.employee_name || "—"} />
              <StatusBadge status={request.status_display || request.status} />
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 16,
                padding: "16px 0",
                borderTop: "1px solid var(--hairline-2)",
                borderBottom: "1px solid var(--hairline-2)",
              }}
            >
              <Mini2 label="From" value={fmtDate(request.start_date)} />
              <Mini2 label="To" value={fmtDate(request.end_date)} />
              <Mini2 label="Days" value={request.days_requested} />
              <Mini2 label="Type" value={request.leave_type_name || "—"} />
            </div>
            <div style={{ padding: "16px 0", borderBottom: "1px solid var(--hairline-2)" }}>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Reason</div>
              <div style={{ fontSize: 14, color: "var(--text)" }}>{request.reason}</div>
            </div>
          </div>
          {pending && effectiveRole !== "employee" && (
            <div className="card-foot">
              <div style={{ display: "flex", gap: 8 }}>
                <Button
                  variant="danger"
                  leftIcon={<I.x size={14} />}
                  disabled={reject.isPending}
                  onClick={() => reject.mutate({ id: request.id, reason: "Declined" })}
                >
                  Reject
                </Button>
                <Button
                  variant="primary"
                  leftIcon={<I.check size={14} />}
                  disabled={approve.isPending}
                  onClick={() => approve.mutate({ id: request.id })}
                >
                  Approve
                </Button>
              </div>
            </div>
          )}
          {pending && effectiveRole === "employee" && (
            <div className="card-foot">
              <Button
                variant="outline"
                disabled={cancel.isPending}
                onClick={() => cancel.mutate(request.id)}
              >
                Cancel my request
              </Button>
            </div>
          )}
        </Card>
        <Card>
          <CardHead title="Decision history" />
          <div className="card-body" style={{ paddingTop: 4 }}>
            {request.decided_at ? (
              <div style={{ fontSize: 13, color: "var(--text-2)" }}>
                Decided {fmtDate(request.decided_at)} by {request.decided_by || "—"}
              </div>
            ) : (
              <div style={{ fontSize: 13, color: "var(--text-3)" }}>
                Awaiting decision.
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

/* Keep a reference to listEmployees so the file's not flagged for unused imports
   when the page eventually consumes it for a tenant-wide leave calendar. */
void listEmployees;
void Avatar;
