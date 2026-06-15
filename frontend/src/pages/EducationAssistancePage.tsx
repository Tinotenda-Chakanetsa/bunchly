import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  ApprovalTimeline,
  Badge,
  Button,
  Card,
  CardHead,
  Donut,
  Drawer,
  Modal,
  PageHeader,
  Pagination,
  PersonCell,
  StatusBadge,
  useToast,
  usePaginated,
} from "@/components/ui";
import { downloadCsv } from "@/lib/export";
import { useAuth } from "@/store/auth";
import {
  hrApproveClaim,
  hrRejectClaim,
  listDependants,
  listEducationClaims,
  markClaimPaid,
  submitEducationClaim,
  type EducationClaim,
} from "@/api/education";

function HeroSummary({
  ytdPaid,
  pending,
  count,
}: {
  ytdPaid: number;
  pending: number;
  count: number;
}) {
  return (
    <Card tone="ink">
      <div style={{ padding: 28 }}>
        <span className="eyebrow" style={{ color: "var(--yellow)" }}>2026 · year to date</span>
        <h2 style={{ fontSize: 38, color: "#fff", margin: "8px 0", letterSpacing: "-0.015em" }}>
          ${ytdPaid.toLocaleString()} paid · {count} active claims.
        </h2>
        <p style={{ color: "rgba(255,255,255,0.7)", fontSize: 14, margin: 0, maxWidth: 500 }}>
          Up to $2,400 per child per year, covering primary, secondary and tertiary fees. Reviewed
          by HR, paid by Accounts.
        </p>
        <div
          style={{
            display: "flex",
            gap: 24,
            marginTop: 24,
            paddingTop: 18,
            borderTop: "1px solid rgba(255,255,255,0.1)",
            flexWrap: "wrap",
          }}
        >
          <div>
            <div className="eyebrow" style={{ color: "rgba(255,255,255,0.5)" }}>Total paid</div>
            <div style={{ fontSize: 26, color: "#fff", marginTop: 4 }}>${ytdPaid.toLocaleString()}</div>
          </div>
          <div>
            <div className="eyebrow" style={{ color: "rgba(255,255,255,0.5)" }}>Pending</div>
            <div style={{ fontSize: 26, color: "var(--yellow)", marginTop: 4 }}>${pending.toLocaleString()}</div>
          </div>
          <div>
            <div className="eyebrow" style={{ color: "rgba(255,255,255,0.5)" }}>Claims</div>
            <div style={{ fontSize: 26, color: "#fff", marginTop: 4 }}>{count}</div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function SpendByLevelCard({ claims }: { claims: EducationClaim[] }) {
  const totals = useMemo(() => {
    const t: Record<string, number> = { primary: 0, secondary: 0, tertiary: 0 };
    claims
      .filter((c) => c.status === "paid")
      .forEach((c) => {
        const key = (c.education_level || "").toLowerCase();
        t[key] = (t[key] || 0) + Number(c.amount_paid || c.amount_claimed || 0);
      });
    return t;
  }, [claims]);
  const total = totals.primary + totals.secondary + totals.tertiary;
  return (
    <Card>
      <CardHead title="Spend by level" sub="Live, from paid claims" />
      <div className="card-body" style={{ display: "flex", gap: 24, alignItems: "center" }}>
        <Donut
          size={140}
          segments={[
            { value: Math.max(totals.primary, 1), color: "var(--action)" },
            { value: Math.max(totals.secondary, 1), color: "var(--yellow)" },
            { value: Math.max(totals.tertiary, 1), color: "var(--bunchly)" },
          ]}
          label={`$${Math.round(total / 1000)}k`}
          sub="paid"
        />
        <div style={{ flex: 1, fontSize: 13 }}>
          {[
            { c: "var(--action)", l: "Primary", v: totals.primary },
            { c: "var(--yellow)", l: "Secondary", v: totals.secondary },
            { c: "var(--bunchly)", l: "Tertiary", v: totals.tertiary },
          ].map((s, i, arr) => (
            <div
              key={i}
              style={{
                padding: "6px 0",
                borderBottom: i === arr.length - 1 ? "none" : "1px solid var(--hairline-2)",
                display: "flex",
                justifyContent: "space-between",
              }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 10, height: 10, borderRadius: 3, background: s.c }} /> {s.l}
              </span>
              <span style={{ fontWeight: 600 }}>${s.v.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

function ClaimDrawer({ claim, onClose }: { claim: EducationClaim | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [paymentRef, setPaymentRef] = useState("");

  const approve = useMutation({
    mutationFn: (vars: { id: string; amount: number }) =>
      hrApproveClaim(vars.id, vars.amount),
    onSuccess: () => {
      toast.push("Approved — routed to Accounts", "success");
      queryClient.invalidateQueries({ queryKey: ["education-claims"] });
      onClose();
    },
  });
  const reject = useMutation({
    mutationFn: (vars: { id: string; reason: string }) => hrRejectClaim(vars.id, vars.reason),
    onSuccess: () => {
      toast.push("Rejected", "error");
      queryClient.invalidateQueries({ queryKey: ["education-claims"] });
      onClose();
    },
  });
  const pay = useMutation({
    mutationFn: () =>
      markClaimPaid({
        id: claim!.id,
        amount_paid: Number(claim!.amount_approved || claim!.amount_claimed),
        payment_reference: paymentRef,
      }),
    onSuccess: () => {
      toast.push("Marked paid", "success");
      queryClient.invalidateQueries({ queryKey: ["education-claims"] });
      onClose();
    },
  });

  if (!claim) return null;
  const stages: Array<{
    who: string;
    when: string;
    what?: string;
    state: "done" | "active" | "rejected" | "";
  }> = [
    {
      who: "Employee submitted",
      when: claim.submitted_at || claim.created_at,
      state: "done",
    },
    {
      who: "HR review",
      when: claim.approved_at
        ? `Approved ${claim.approved_at}`
        : claim.status === "pending_hr"
          ? "Awaiting decision"
          : "—",
      state:
        claim.status === "pending_hr"
          ? "active"
          : claim.status === "rejected"
            ? "rejected"
            : "done",
    },
    {
      who: "Accounts payment",
      when: claim.paid_at
        ? `Paid ${claim.paid_at}`
        : claim.status === "pending_payment"
          ? "Scheduled"
          : "Pending HR",
      state:
        claim.status === "paid" ? "done" : claim.status === "pending_payment" ? "active" : "",
    },
  ];

  return (
    <Drawer
      open={!!claim}
      onClose={onClose}
      title={`Claim ${claim.id.slice(0, 8)}`}
      sub={`${claim.employee_name || "—"} · ${claim.dependant_name || ""}`}
      footer={
        claim.status === "pending_hr" ? (
          <>
            <Button
              variant="danger"
              disabled={reject.isPending}
              onClick={() => reject.mutate({ id: claim.id, reason: "Declined" })}
            >
              Reject
            </Button>
            <Button
              variant="primary"
              disabled={approve.isPending}
              onClick={() =>
                approve.mutate({
                  id: claim.id,
                  amount: Number(claim.amount_claimed),
                })
              }
            >
              Approve & route to Accounts
            </Button>
          </>
        ) : claim.status === "pending_payment" ? (
          <>
            <input
              className="input"
              style={{ maxWidth: 200, marginRight: 8 }}
              placeholder="Payment reference"
              value={paymentRef}
              onChange={(e) => setPaymentRef(e.target.value)}
            />
            <Button
              variant="primary"
              disabled={pay.isPending || !paymentRef.trim()}
              onClick={() => pay.mutate()}
            >
              Mark as paid
            </Button>
          </>
        ) : (
          <Button variant="primary" onClick={onClose}>
            Close
          </Button>
        )
      }
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <div>
          <div className="eyebrow">Amount claimed</div>
          <div style={{ fontSize: 30, color: "var(--ink-3)", marginTop: 4 }}>
            ${Number(claim.amount_claimed).toLocaleString()}
          </div>
        </div>
        <div>
          <div className="eyebrow">Approved</div>
          <div style={{ fontSize: 30, color: "var(--ink-3)", marginTop: 4 }}>
            ${Number(claim.amount_approved || 0).toLocaleString()}
          </div>
        </div>
      </div>

      <div className="eyebrow" style={{ marginBottom: 10 }}>Approval flow</div>
      <ApprovalTimeline nodes={stages} />

      {claim.payment_reference && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            background: "var(--card-2)",
            borderRadius: 10,
            fontSize: 13,
          }}
        >
          <div className="eyebrow" style={{ marginBottom: 4 }}>Payment reference</div>
          <div style={{ fontFamily: "var(--mono)" }}>{claim.payment_reference}</div>
        </div>
      )}
    </Drawer>
  );
}

function SubmitClaimModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { user } = useAuth();
  const dependants = useQuery({
    queryKey: ["dependants", "mine"],
    queryFn: () => listDependants(user?.id),
    enabled: open && Boolean(user?.id),
  });
  const [dependant, setDependant] = useState("");
  const [period, setPeriod] = useState("Term 2 2026");
  const [level, setLevel] = useState("primary");
  const [institution, setInstitution] = useState("");
  const [amount, setAmount] = useState(1200);

  const submit = useMutation({
    mutationFn: submitEducationClaim,
    onSuccess: () => {
      toast.push("Claim submitted — HR will review", "success");
      queryClient.invalidateQueries({ queryKey: ["education-claims"] });
      onClose();
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not submit",
        "error",
      ),
  });

  function handle(e: FormEvent) {
    e.preventDefault();
    if (!dependant) {
      toast.push("Pick a dependant first", "error");
      return;
    }
    submit.mutate({
      dependant,
      education_level: level,
      academic_period: period,
      institution_name: institution || "—",
      amount_claimed: amount,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Submit education assistance claim"
      sub="Up to $2,400 per child, per year."
      width={640}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handle} disabled={submit.isPending}>
            {submit.isPending ? "Submitting…" : "Submit for HR review"}
          </Button>
        </>
      }
    >
      <form onSubmit={handle}>
        <div className="field" style={{ marginBottom: 14 }}>
          <label>Dependant</label>
          <select
            className="select"
            value={dependant}
            onChange={(e) => setDependant(e.target.value)}
          >
            <option value="">
              {dependants.isLoading
                ? "Loading…"
                : dependants.data && dependants.data.length === 0
                  ? "No dependants registered — add one first"
                  : "Pick a dependant"}
            </option>
            {(dependants.data || []).map((d) => (
              <option key={d.id} value={d.id}>
                {d.first_name} {d.last_name} · {d.education_level}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-2" style={{ marginBottom: 14 }}>
          <div className="field">
            <label>Academic period</label>
            <input className="input" value={period} onChange={(e) => setPeriod(e.target.value)} />
          </div>
          <div className="field">
            <label>Education level</label>
            <select className="select" value={level} onChange={(e) => setLevel(e.target.value)}>
              <option value="primary">Primary</option>
              <option value="secondary">Secondary</option>
              <option value="tertiary">Tertiary</option>
            </select>
          </div>
          <div className="field">
            <label>Institution</label>
            <input
              className="input"
              value={institution}
              onChange={(e) => setInstitution(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Amount (USD)</label>
            <input
              className="input"
              type="number"
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
            />
          </div>
        </div>
      </form>
    </Modal>
  );
}

export default function EducationAssistancePage() {
  const { effectiveRole } = useAuth();
  const [drawer, setDrawer] = useState<EducationClaim | null>(null);
  const [showSubmit, setShowSubmit] = useState(false);

  const claims = useQuery({
    queryKey: ["education-claims"],
    queryFn: () => listEducationClaims(),
  });
  const rows = claims.data?.results ?? [];

  const ytdPaid = useMemo(
    () =>
      rows
        .filter((c) => c.status === "paid")
        .reduce((a, c) => a + Number(c.amount_paid || c.amount_claimed || 0), 0),
    [rows],
  );
  const pending = useMemo(
    () =>
      rows
        .filter((c) => c.status === "pending_hr" || c.status === "pending_payment")
        .reduce((a, c) => a + Number(c.amount_claimed), 0),
    [rows],
  );

  const pag = usePaginated(rows);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Benefits"
        title="Education Assistance"
        lede={
          claims.isLoading
            ? "Loading…"
            : "School fees claims, dependants, and benefit eligibility rules."
        }
        actions={
          <Button
            variant="outline"
            size="sm"
            leftIcon={<I.download size={14} />}
            onClick={() =>
              downloadCsv(
                `education-claims-${new Date().toISOString().slice(0, 10)}.csv`,
                rows,
              )
            }
          >
            Export
          </Button>
        }
      />
      <div className="grid" style={{ gridTemplateColumns: "1.4fr 1fr", gap: 16, marginBottom: 20 }}>
        <HeroSummary ytdPaid={ytdPaid} pending={pending} count={rows.length} />
        <SpendByLevelCard claims={rows} />
      </div>
      <div className="spread" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0, fontSize: 22, color: "var(--ink-3)" }}>
          {effectiveRole === "employee" ? "My claims" : "All claims"}
        </h2>
        <Button
          variant="primary"
          size="sm"
          leftIcon={<I.plus size={14} />}
          onClick={() => setShowSubmit(true)}
        >
          Submit claim
        </Button>
      </div>
      <Card>
        <table className="table">
          <thead>
            <tr>
              <th>Claim</th>
              <th>Employee</th>
              <th>Dependant</th>
              <th>Level</th>
              <th>Amount</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {pag.slice.map((c) => (
              <tr key={c.id} className="clickable" onClick={() => setDrawer(c)}>
                <td>
                  <div style={{ fontWeight: 500, fontFamily: "var(--mono)", fontSize: 12 }}>
                    {c.id.slice(0, 8)}
                  </div>
                  <div style={{ fontSize: 11.5, color: "var(--text-3)" }}>{c.academic_period}</div>
                </td>
                <td>
                  <PersonCell name={c.employee_name || "—"} sub={c.institution_name} />
                </td>
                <td>{c.dependant_name || "—"}</td>
                <td>
                  <Badge tone={c.education_level === "primary" ? "blue" : c.education_level === "secondary" ? "yellow" : "outline"}>
                    {c.education_level}
                  </Badge>
                </td>
                <td className="num">
                  <span style={{ fontSize: 18, color: "var(--ink-3)" }}>
                    ${Number(c.amount_claimed).toLocaleString()}
                  </span>
                </td>
                <td>
                  <StatusBadge status={c.status_display || c.status} />
                </td>
                <td style={{ textAlign: "right" }}>
                  <I.chevron size={14} style={{ color: "var(--text-3)" }} />
                </td>
              </tr>
            ))}
            {rows.length === 0 && claims.isFetched && (
              <tr>
                <td colSpan={7}>
                  <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                    No claims yet.
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
      <ClaimDrawer claim={drawer} onClose={() => setDrawer(null)} />
      <SubmitClaimModal open={showSubmit} onClose={() => setShowSubmit(false)} />
    </div>
  );
}
