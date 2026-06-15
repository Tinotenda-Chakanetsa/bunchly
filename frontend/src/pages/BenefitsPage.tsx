import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Badge,
  Button,
  Card,
  CardHead,
  Donut,
  KpiCell,
  KpiStrip,
  Modal,
  PageHeader,
  Pagination,
  PersonCell,
  Tabs,
  useToast,
  usePaginated,
} from "@/components/ui";
import { downloadCsv } from "@/lib/export";
import { useAuth } from "@/store/auth";
import {
  approveBenefitEnrolment,
  createBenefitType,
  declineBenefitEnrolment,
  enrolBenefit,
  listBenefitTypes,
  listEmployeeBenefits,
  terminateBenefitEnrolment,
  type BenefitType,
  type EmployeeBenefit,
} from "@/api/benefits";
import { listEducationClaims } from "@/api/education";
import { listEmployees } from "@/api/employees";

/* ---------- modals ---------- */

function AddBenefitModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [provider, setProvider] = useState("");
  const [category, setCategory] = useState("health");
  const [employeeContribution, setEmployeeContribution] = useState("0");
  const [employerContribution, setEmployerContribution] = useState("0");
  const [requiresApproval, setRequiresApproval] = useState(true);
  const [coversDependants, setCoversDependants] = useState(true);
  const [eligibilityMinMonths, setEligibilityMinMonths] = useState(0);

  const mutation = useMutation({
    mutationFn: () =>
      createBenefitType({
        name: name.trim(),
        code: code.trim() || name.trim().toUpperCase().replace(/[^A-Z0-9]+/g, "_").slice(0, 12),
        category,
        provider: provider.trim() || undefined,
        contribution_basis: "fixed",
        employee_contribution: employeeContribution,
        employer_contribution: employerContribution,
        is_taxable: false,
        requires_approval: requiresApproval,
        covers_dependants: coversDependants,
        eligibility_min_months: eligibilityMinMonths,
        is_active: true,
      }),
    onSuccess: () => {
      toast.push(`Benefit '${name}' added`, "success");
      queryClient.invalidateQueries({ queryKey: ["benefit-types"] });
      onClose();
      setName("");
      setCode("");
      setProvider("");
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data;
      const firstKey = data && Object.keys(data)[0];
      const msg =
        firstKey && Array.isArray(data?.[firstKey])
          ? `${firstKey}: ${(data[firstKey] as string[])[0]}`
          : (data as { detail?: string })?.detail || "Could not create benefit";
      toast.push(msg, "error");
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      toast.push("Name is required", "error");
      return;
    }
    mutation.mutate();
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add benefit"
      sub="A new tile appears in the catalog immediately."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !name.trim()}
          >
            {mutation.isPending ? "Saving…" : "Add benefit"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="grid grid-2" style={{ gap: 14 }}>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Benefit name</label>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Private dental cover"
              autoFocus
            />
          </div>
          <div className="field">
            <label>Code (optional)</label>
            <input
              className="input"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Auto-generated from name"
              maxLength={32}
            />
          </div>
          <div className="field">
            <label>Category</label>
            <select className="select" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="health">Health</option>
              <option value="dental">Dental</option>
              <option value="vision">Vision</option>
              <option value="life">Life insurance</option>
              <option value="disability">Disability</option>
              <option value="retirement">Retirement</option>
              <option value="education">Education</option>
              <option value="wellness">Wellness</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="field">
            <label>Provider</label>
            <input
              className="input"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              placeholder="Discovery"
            />
          </div>
          <div className="field">
            <label>Eligibility (months in role)</label>
            <input
              className="input"
              type="number"
              min={0}
              value={eligibilityMinMonths}
              onChange={(e) => setEligibilityMinMonths(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label>Employee contribution</label>
            <input
              className="input"
              value={employeeContribution}
              onChange={(e) => setEmployeeContribution(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Employer contribution</label>
            <input
              className="input"
              value={employerContribution}
              onChange={(e) => setEmployerContribution(e.target.value)}
            />
          </div>
          <div className="field" style={{ gridColumn: "1 / -1", display: "flex", gap: 16 }}>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={requiresApproval}
                onChange={(e) => setRequiresApproval(e.target.checked)}
              />
              Requires HR approval
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={coversDependants}
                onChange={(e) => setCoversDependants(e.target.checked)}
              />
              Covers dependants
            </label>
          </div>
        </div>
      </form>
    </Modal>
  );
}

function EnrolModal({
  open,
  onClose,
  benefit,
}: {
  open: boolean;
  onClose: () => void;
  benefit: BenefitType | null;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const employeesQ = useQuery({
    queryKey: ["employees", "for-enrol"],
    queryFn: () => listEmployees(),
    enabled: open,
  });
  const [employee, setEmployee] = useState("");
  const [notes, setNotes] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      enrolBenefit({
        employee: employee || undefined,
        benefit_type: benefit!.id,
        notes: notes.trim() || undefined,
      }),
    onSuccess: () => {
      toast.push(`Enrolled in ${benefit?.name}`, "success");
      queryClient.invalidateQueries({ queryKey: ["employee-benefits"] });
      queryClient.invalidateQueries({ queryKey: ["benefit-types"] });
      onClose();
      setEmployee("");
      setNotes("");
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data;
      const firstKey = data && Object.keys(data)[0];
      const msg =
        firstKey && Array.isArray(data?.[firstKey])
          ? `${firstKey}: ${(data[firstKey] as string[])[0]}`
          : (data as { detail?: string })?.detail || "Could not enrol";
      toast.push(msg, "error");
    },
  });

  return (
    <Modal
      open={open && !!benefit}
      onClose={onClose}
      title={`Enrol · ${benefit?.name ?? ""}`}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Enrolling…" : "Enrol"}
          </Button>
        </>
      }
    >
      <div className="grid grid-2" style={{ gap: 14 }}>
        <div className="field" style={{ gridColumn: "1 / -1" }}>
          <label>Employee</label>
          <select
            className="select"
            value={employee}
            onChange={(e) => setEmployee(e.target.value)}
          >
            <option value="">— Enrol myself —</option>
            {(employeesQ.data?.results ?? []).map((e) => (
              <option key={e.id} value={e.id}>
                {e.full_name}
              </option>
            ))}
          </select>
        </div>
        <div className="field" style={{ gridColumn: "1 / -1" }}>
          <label>Notes (optional)</label>
          <textarea
            className="textarea"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Plan choice, dependants, etc."
          />
        </div>
      </div>
    </Modal>
  );
}

/* ---------- sub-views ---------- */

function BenefitsOverview({
  benefits,
  enrolments,
  onEnrol,
}: {
  benefits: BenefitType[];
  enrolments: EmployeeBenefit[];
  onEnrol: (b: BenefitType) => void;
}) {
  const activeEnrolments = enrolments.filter((e) => e.status === "active").length;
  const avgTakeUp =
    benefits.length === 0
      ? 0
      : Math.round(
          (benefits.reduce((a, b) => {
            const enrolled = b.enrolment_count ?? 0;
            return a + enrolled;
          }, 0) /
            Math.max(1, benefits.length * 10)) *
            100,
        );

  return (
    <>
      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="Active benefits" value={benefits.length} sub="In your catalog" />
        <KpiCell label="Active enrolments" value={activeEnrolments} sub="Across all benefits" />
        <KpiCell label="Pending approval" value={enrolments.filter((e) => e.status === "pending").length} />
        <KpiCell label="Providers" value={new Set(benefits.map((b) => b.provider).filter(Boolean)).size} />
      </KpiStrip>

      {benefits.length === 0 ? (
        <Card>
          <div className="empty" style={{ margin: 16 }}>
            <div className="title">No benefits in your catalog yet</div>
            <div className="lede">Click <strong>Add benefit</strong> above to create one.</div>
          </div>
        </Card>
      ) : (
        <div className="grid grid-3">
          {benefits.map((b) => {
            const enrolled = b.enrolment_count ?? 0;
            return (
              <Card key={b.id}>
                <div style={{ padding: 18 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      marginBottom: 12,
                    }}
                  >
                    <span className="eyebrow">{b.code}</span>
                    <Badge tone="outline">{b.category_display || b.category}</Badge>
                  </div>
                  <h3
                    style={{
                      fontSize: 22,
                      color: "var(--ink-3)",
                      margin: "0 0 4px",
                      letterSpacing: "-0.01em",
                    }}
                  >
                    {b.name}
                  </h3>
                  <div style={{ color: "var(--text-3)", fontSize: 13 }}>
                    {b.provider || "—"}
                  </div>
                  <div className="divider" />
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 12 }}>
                    <div>
                      <div style={{ color: "var(--text-3)" }}>Enrolled</div>
                      <div style={{ fontSize: 22, color: "var(--ink-3)" }}>{enrolled}</div>
                    </div>
                    <div>
                      <div style={{ color: "var(--text-3)" }}>Contributions</div>
                      <div style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 4 }}>
                        Emp {b.employee_contribution || "0"} / Co {b.employer_contribution || "0"}
                      </div>
                    </div>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginTop: 12,
                      fontSize: 11.5,
                      color: "var(--text-3)",
                    }}
                  >
                    <span>Eligible after {b.eligibility_min_months}mo</span>
                    <span>
                      {b.requires_approval ? "HR approval" : "Self-service"} ·{" "}
                      {b.covers_dependants ? "+ dependants" : "employee only"}
                    </span>
                  </div>
                  <Button
                    variant="primary"
                    size="sm"
                    style={{ marginTop: 12, width: "100%" }}
                    onClick={() => onEnrol(b)}
                  >
                    Enrol
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}

function EnrolmentsView({ enrolments }: { enrolments: EmployeeBenefit[] }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const pag = usePaginated(enrolments);

  const approve = useMutation({
    mutationFn: (id: string) => approveBenefitEnrolment(id),
    onSuccess: () => {
      toast.push("Enrolment approved", "success");
      queryClient.invalidateQueries({ queryKey: ["employee-benefits"] });
    },
    onError: () => toast.push("Could not approve", "error"),
  });
  const decline = useMutation({
    mutationFn: (id: string) => declineBenefitEnrolment(id),
    onSuccess: () => {
      toast.push("Enrolment declined", "success");
      queryClient.invalidateQueries({ queryKey: ["employee-benefits"] });
    },
    onError: () => toast.push("Could not decline", "error"),
  });
  const terminate = useMutation({
    mutationFn: (id: string) => terminateBenefitEnrolment(id),
    onSuccess: () => {
      toast.push("Enrolment terminated", "success");
      queryClient.invalidateQueries({ queryKey: ["employee-benefits"] });
    },
    onError: () => toast.push("Could not terminate", "error"),
  });

  if (enrolments.length === 0) {
    return (
      <Card>
        <div className="empty">
          <div className="title">No enrolments yet</div>
          <div className="lede">Click "Enrol" on any benefit tile to add the first enrolment.</div>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHead title="Enrolments" sub="Live, per employee" />
      <table className="table">
        <thead>
          <tr>
            <th>Employee</th>
            <th>Benefit</th>
            <th>Status</th>
            <th>Since</th>
            <th style={{ textAlign: "right" }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {pag.slice.map((e) => (
            <tr key={e.id}>
              <td>
                <PersonCell name={e.employee_name || "—"} sub={e.notes} />
              </td>
              <td>{e.benefit_type_name || "—"}</td>
              <td>
                <Badge tone={e.status === "active" ? "green" : e.status === "pending" ? "yellow" : "outline"}>
                  {e.status_display || e.status}
                </Badge>
              </td>
              <td className="muted">
                {e.start_date ? new Date(e.start_date).toLocaleDateString() : "—"}
              </td>
              <td style={{ textAlign: "right" }}>
                <div style={{ display: "inline-flex", gap: 4 }}>
                  {e.status === "pending" && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => decline.mutate(e.id)}
                        disabled={decline.isPending}
                      >
                        Decline
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => approve.mutate(e.id)}
                        disabled={approve.isPending}
                      >
                        Approve
                      </Button>
                    </>
                  )}
                  {e.status === "active" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => terminate.mutate(e.id)}
                      disabled={terminate.isPending}
                    >
                      Terminate
                    </Button>
                  )}
                </div>
              </td>
            </tr>
          ))}
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

function RulesEngine({ benefits }: { benefits: BenefitType[] }) {
  if (benefits.length === 0) {
    return (
      <Card>
        <div className="empty" style={{ margin: 16 }}>
          <div className="title">No rules to show</div>
          <div className="lede">Add a benefit type first; its rules appear here automatically.</div>
        </div>
      </Card>
    );
  }
  return (
    <div className="grid grid-2">
      {benefits.map((b) => (
        <Card key={b.id}>
          <div style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <span className="eyebrow">Rule set</span>
                <h3 style={{ fontSize: 20, color: "var(--ink-3)", margin: "4px 0" }}>{b.name}</h3>
              </div>
              <Badge tone={b.is_active ? "green" : "outline"}>{b.is_active ? "Active" : "Inactive"}</Badge>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 10,
                marginTop: 12,
                fontSize: 12.5,
              }}
            >
              <div>
                <div style={{ color: "var(--text-3)" }}>Eligibility</div>
                <div style={{ fontWeight: 500 }}>
                  {b.eligibility_min_months}mo in role
                </div>
              </div>
              <div>
                <div style={{ color: "var(--text-3)" }}>Contribution basis</div>
                <div style={{ fontWeight: 500 }}>{b.contribution_basis || "—"}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-3)" }}>Approval</div>
                <div style={{ fontWeight: 500 }}>
                  {b.requires_approval ? "HR approval" : "Self-service"}
                </div>
              </div>
              <div>
                <div style={{ color: "var(--text-3)" }}>Dependants</div>
                <div style={{ fontWeight: 500 }}>
                  {b.covers_dependants ? "Covered" : "Employee only"}
                </div>
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

function SpendInsights({ benefits }: { benefits: BenefitType[] }) {
  /* Education-assistance is paid through a dedicated module; we surface
     its paid totals here so HR sees benefits spend in one place. */
  const educationQ = useQuery({
    queryKey: ["education-claims", "paid"],
    queryFn: () => listEducationClaims({ status: "paid" }),
  });
  const paidClaims = educationQ.data?.results ?? [];

  const totalEdu = paidClaims.reduce((a, c) => a + Number(c.amount_paid || c.amount_claimed || 0), 0);
  const totals = useMemo(() => {
    const t: Record<string, number> = { Primary: 0, Secondary: 0, Tertiary: 0 };
    paidClaims.forEach((c) => {
      const level = c.education_level || "";
      const display =
        level === "primary" ? "Primary" : level === "secondary" ? "Secondary" : "Tertiary";
      t[display] = (t[display] || 0) + Number(c.amount_paid || c.amount_claimed || 0);
    });
    return t;
  }, [paidClaims]);

  return (
    <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      <Card>
        <CardHead title="Education assistance spend" sub="Live, by level (paid only)" />
        <div className="card-body" style={{ display: "flex", gap: 24, alignItems: "center" }}>
          <Donut
            size={140}
            segments={[
              { value: Math.max(totals.Primary, 1), color: "var(--action)" },
              { value: Math.max(totals.Secondary, 1), color: "var(--yellow)" },
              { value: Math.max(totals.Tertiary, 1), color: "var(--bunchly)" },
            ]}
            label={`$${Math.round(totalEdu / 1000)}k`}
            sub="paid"
          />
          <div style={{ flex: 1, fontSize: 13 }}>
            {[
              { c: "var(--action)", l: "Primary", v: totals.Primary },
              { c: "var(--yellow)", l: "Secondary", v: totals.Secondary },
              { c: "var(--bunchly)", l: "Tertiary", v: totals.Tertiary },
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
      <Card>
        <CardHead title="Enrolment count by benefit" sub="Live, from your catalog" />
        <div className="card-body">
          {benefits.length === 0 ? (
            <div style={{ fontSize: 13, color: "var(--text-3)" }}>
              No benefits to show yet.
            </div>
          ) : (
            benefits.map((b, i, arr) => (
              <div
                key={b.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 0",
                  borderBottom: i === arr.length - 1 ? "none" : "1px solid var(--hairline-2)",
                  fontSize: 13,
                }}
              >
                <span>{b.name}</span>
                <span style={{ fontWeight: 600 }}>{b.enrolment_count ?? 0}</span>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}

/* ---------- page ---------- */

export default function BenefitsPage() {
  const { effectiveRole } = useAuth();
  const [tab, setTab] = useState("overview");
  const [showAdd, setShowAdd] = useState(false);
  const [enrolTarget, setEnrolTarget] = useState<BenefitType | null>(null);

  const benefitsQ = useQuery({ queryKey: ["benefit-types"], queryFn: listBenefitTypes });
  const enrolmentsQ = useQuery({
    queryKey: ["employee-benefits"],
    queryFn: () => listEmployeeBenefits(),
  });

  const benefits = benefitsQ.data ?? [];
  const enrolments = enrolmentsQ.data?.results ?? [];

  return (
    <div className="page">
      <PageHeader
        eyebrow="Benefits & wellness"
        title="Benefits"
        lede={
          benefitsQ.isLoading
            ? "Loading…"
            : `${benefits.length} benefits · ${enrolments.length} active enrolments`
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={() => downloadCsv("benefits.csv", benefits)}
            >
              Export
            </Button>
            {effectiveRole !== "employee" && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.plus size={14} />}
                onClick={() => setShowAdd(true)}
              >
                Add benefit
              </Button>
            )}
          </>
        }
      />
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "overview", label: "Overview" },
          { value: "enrol", label: "Enrolments", count: enrolments.length },
          { value: "rules", label: "Rules & eligibility" },
          { value: "spend", label: "Spend insights" },
        ]}
      />
      {tab === "overview" && (
        <BenefitsOverview
          benefits={benefits}
          enrolments={enrolments}
          onEnrol={(b) => setEnrolTarget(b)}
        />
      )}
      {tab === "enrol" && <EnrolmentsView enrolments={enrolments} />}
      {tab === "rules" && <RulesEngine benefits={benefits} />}
      {tab === "spend" && <SpendInsights benefits={benefits} />}

      <AddBenefitModal open={showAdd} onClose={() => setShowAdd(false)} />
      <EnrolModal
        open={!!enrolTarget}
        onClose={() => setEnrolTarget(null)}
        benefit={enrolTarget}
        key={enrolTarget?.id || "enrol"}
      />
    </div>
  );
}
