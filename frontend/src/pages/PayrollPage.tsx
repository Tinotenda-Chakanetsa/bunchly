import { useMemo, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  ApprovalTimeline,
  BarChart,
  Button,
  Card,
  CardHead,
  ColumnChart,
  KpiCell,
  KpiStrip,
  Modal,
  PageHeader,
  Pagination,
  StatusBadge,
  Tabs,
  useToast,
  usePaginated,
} from "@/components/ui";
import { downloadBlob, downloadCsv } from "@/lib/export";
import { useAuth } from "@/store/auth";
import {
  approvePayrollPeriod,
  createPayrollPeriod,
  exportPayrollPeriod,
  generatePayrollRecords,
  generatePayslips,
  getPayrollPeriod,
  listPayrollPeriods,
  listPayrollRecords,
  markPayrollPeriodPaid,
  publishPayslips,
  type PayrollPeriod,
  type PayrollRecord,
} from "@/api/payroll";
import { listEmployees } from "@/api/employees";

function moneyOf(value?: string | null): string {
  if (!value) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function RunPayrollModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const now = new Date();
  const defaultName = now.toLocaleDateString("en-GB", { month: "long", year: "numeric" });
  const defaultCode = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const first = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);
  const defaultPay = new Date(now.getFullYear(), now.getMonth(), 25).toISOString().slice(0, 10);

  const [name, setName] = useState(defaultName);
  const [code, setCode] = useState(defaultCode);
  const [startDate, setStartDate] = useState(first);
  const [endDate, setEndDate] = useState(last);
  const [payDate, setPayDate] = useState(defaultPay);

  const create = useMutation({
    mutationFn: () =>
      createPayrollPeriod({
        name: name.trim(),
        code: code.trim(),
        start_date: startDate,
        end_date: endDate,
        pay_date: payDate,
      }),
    onSuccess: async (period) => {
      try {
        const summary = await generatePayrollRecords(period.id);
        toast.push(
          `${period.code} started · ${summary.records_created} record${summary.records_created === 1 ? "" : "s"} generated`,
          "success",
        );
      } catch {
        toast.push(`${period.code} created — generate records manually`, "success");
      }
      queryClient.invalidateQueries({ queryKey: ["payroll-periods"] });
      onClose();
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data;
      const firstKey = data && Object.keys(data)[0];
      const msg =
        firstKey && Array.isArray(data?.[firstKey])
          ? `${firstKey}: ${(data[firstKey] as string[])[0]}`
          : (data as { detail?: string })?.detail || "Could not start payroll";
      toast.push(msg, "error");
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !code.trim()) {
      toast.push("Name + code are required", "error");
      return;
    }
    create.mutate();
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Run payroll"
      sub="Creates a period + generates per-employee records from current contracts."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={create.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => create.mutate()}
            disabled={create.isPending}
          >
            {create.isPending ? "Starting…" : "Run"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="grid grid-2" style={{ gap: 14 }}>
        <div className="field" style={{ gridColumn: "1 / -1" }}>
          <label>Period name</label>
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
        </div>
        <div className="field">
          <label>Code</label>
          <input className="input" value={code} onChange={(e) => setCode(e.target.value)} />
        </div>
        <div className="field">
          <label>Pay date</label>
          <input
            className="input"
            type="date"
            value={payDate}
            onChange={(e) => setPayDate(e.target.value)}
          />
        </div>
        <div className="field">
          <label>Start date</label>
          <input
            className="input"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>
        <div className="field">
          <label>End date</label>
          <input
            className="input"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
      </form>
    </Modal>
  );
}

export default function PayrollPage() {
  const navigate = useNavigate();
  const { hasPerm } = useAuth();
  const canRun = hasPerm("payroll.run_period") || hasPerm("payroll.manage");
  const [tab, setTab] = useState("periods");
  const [showRun, setShowRun] = useState(false);

  const periodsQ = useQuery({
    queryKey: ["payroll-periods"],
    queryFn: () => listPayrollPeriods({ page: 1 }),
  });
  const employeesQ = useQuery({ queryKey: ["employees"], queryFn: () => listEmployees() });

  const periods: PayrollPeriod[] = periodsQ.data?.results ?? [];
  const employees = employeesQ.data?.results ?? [];

  const processingCount = periods.filter(
    (p) => p.status === "draft" || p.status === "processing",
  ).length;
  const paidCount = periods.filter((p) => p.status === "paid").length;
  const pag = usePaginated(periods);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Pay & compensation"
        title="Payroll"
        lede={
          periodsQ.isLoading
            ? "Loading…"
            : `${periods.length} period${periods.length === 1 ? "" : "s"} · ${processingCount} processing`
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={() => downloadCsv("payroll-periods.csv", periods)}
            >
              Export
            </Button>
            {canRun && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.zap size={14} />}
                onClick={() => setShowRun(true)}
              >
                Run payroll
              </Button>
            )}
          </>
        }
      />
      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="Periods" value={periods.length} />
        <KpiCell label="Headcount" value={employeesQ.data?.count ?? employees.length} />
        <KpiCell label="Processing" value={processingCount} />
        <KpiCell label="Paid" value={paidCount} />
      </KpiStrip>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "periods", label: "Pay periods" },
          { value: "reports", label: "Reports" },
        ]}
      />
      {tab === "periods" && (
        <Card>
          {periods.length === 0 && !periodsQ.isLoading ? (
            <div className="empty" style={{ margin: 16 }}>
              <div className="title">No payroll periods yet</div>
              <div className="lede">
                Click <strong>Run payroll</strong> to create your first period.
              </div>
            </div>
          ) : (
            <>
              <table className="table">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th>Records</th>
                    <th>Cut-off</th>
                    <th>Pay date</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {pag.slice.map((p) => (
                    <tr
                      key={p.id}
                      className="clickable"
                      onClick={() => navigate(`/payroll/${p.id}`)}
                    >
                      <td>
                        <div style={{ fontWeight: 600 }}>{p.name}</div>
                        <div style={{ fontSize: 11.5, color: "var(--text-3)" }}>{p.code}</div>
                      </td>
                      <td className="num">{p.record_count ?? 0}</td>
                      <td className="muted num">{p.end_date}</td>
                      <td className="muted num">{p.pay_date}</td>
                      <td>
                        <StatusBadge status={p.status_display || p.status} />
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <I.chevron size={14} style={{ color: "var(--text-3)" }} />
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
            </>
          )}
        </Card>
      )}
      {tab === "reports" && (
        <div className="grid grid-2">
          <Card>
            <CardHead title="Periods · record counts" />
            <div className="card-body">
              {periods.length === 0 ? (
                <div style={{ color: "var(--text-3)", fontSize: 13 }}>
                  Reports populate once you've run at least one period.
                </div>
              ) : (
                <ColumnChart
                  format={(v) => `${v}`}
                  data={periods
                    .slice(0, 8)
                    .reverse()
                    .map((p) => ({
                      label: p.code.slice(-7),
                      value: p.record_count ?? 0,
                    }))}
                />
              )}
            </div>
          </Card>
          <Card>
            <CardHead title="Headcount by department" />
            <div className="card-body">
              <BarChart
                format={(v) => `${v}`}
                data={Array.from(
                  new Set(employees.map((e) => e.department_name).filter(Boolean) as string[]),
                ).map((d) => ({
                  label: d,
                  value: employees.filter((e) => e.department_name === d).length,
                  color: "var(--action)",
                }))}
              />
            </div>
          </Card>
        </div>
      )}
      <RunPayrollModal open={showRun} onClose={() => setShowRun(false)} />
    </div>
  );
}

export function PeriodDetailPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { id = "" } = useParams();

  const periodQ = useQuery({
    queryKey: ["payroll-period", id],
    queryFn: () => getPayrollPeriod(id),
    enabled: !!id,
  });
  const recordsQ = useQuery({
    queryKey: ["payroll-records", id],
    queryFn: () => listPayrollRecords({ period: id }),
    enabled: !!id,
  });

  const period = periodQ.data;
  const records: PayrollRecord[] = recordsQ.data?.results ?? [];

  const totals = useMemo(() => {
    const sum = (key: keyof PayrollRecord) =>
      records.reduce((a, r) => a + Number((r[key] as string | undefined) || 0), 0);
    return {
      gross: sum("gross_pay"),
      net: sum("net_pay"),
      allowances: sum("total_allowances"),
      deductions: sum("total_deductions"),
    };
  }, [records]);

  const approve = useMutation({
    mutationFn: () => approvePayrollPeriod(id),
    onSuccess: () => {
      toast.push("Period approved", "success");
      queryClient.invalidateQueries({ queryKey: ["payroll-period", id] });
      queryClient.invalidateQueries({ queryKey: ["payroll-periods"] });
    },
    onError: () => toast.push("Approval failed", "error"),
  });

  const markPaid = useMutation({
    mutationFn: () => markPayrollPeriodPaid(id),
    onSuccess: () => {
      toast.push("Period marked as paid", "success");
      queryClient.invalidateQueries({ queryKey: ["payroll-period", id] });
      queryClient.invalidateQueries({ queryKey: ["payroll-periods"] });
    },
    onError: () => toast.push("Could not mark as paid", "error"),
  });

  const publish = useMutation({
    mutationFn: async () => {
      await generatePayslips(id);
      return publishPayslips(id);
    },
    onSuccess: (data) => {
      toast.push(
        `Published ${data.payslips_published} payslip${data.payslips_published === 1 ? "" : "s"}`,
        "success",
      );
      queryClient.invalidateQueries({ queryKey: ["payroll-period", id] });
    },
    onError: () => toast.push("Could not publish payslips", "error"),
  });

  async function downloadBankFile() {
    if (records.length === 0) {
      toast.push(
        "No records to export — generate records first.",
        "error",
      );
      return;
    }
    try {
      const { blob, filename } = await exportPayrollPeriod(id, "csv");
      if (blob.size === 0) {
        toast.push("Server returned an empty file.", "error");
        return;
      }
      downloadBlob(blob, filename);
      toast.push(`Bank file downloaded (${records.length} rows)`, "success");
    } catch (err: unknown) {
      const ax = err as { response?: { status?: number; data?: unknown } };
      if (ax.response?.status === 403) {
        toast.push("You don't have permission to export payroll.", "error");
      } else if (ax.response?.status === 404) {
        toast.push("Period not found.", "error");
      } else if (ax.response?.data instanceof Blob) {
        try {
          const text = await (ax.response.data as Blob).text();
          const parsed = JSON.parse(text);
          toast.push(parsed.detail || "Export failed", "error");
        } catch {
          toast.push("Export failed", "error");
        }
      } else {
        toast.push("Export failed", "error");
      }
    }
  }

  if (periodQ.isLoading) {
    return (
      <div className="page">
        <PageHeader title="Payroll period" lede="Loading…" />
      </div>
    );
  }

  if (!period) {
    return (
      <div className="page">
        <Button variant="ghost" size="sm" onClick={() => navigate("/payroll")}>
          ← Back
        </Button>
        <Card>
          <div className="empty" style={{ margin: 16 }}>
            <div className="title">Period not found</div>
            <div className="lede">
              It may have been deleted, or you don't have access to it.
            </div>
          </div>
        </Card>
      </div>
    );
  }

  const isApproved = period.status === "approved" || period.status === "paid";
  const isPaid = period.status === "paid";

  return (
    <div className="page">
      <Button
        variant="ghost"
        size="sm"
        style={{ marginBottom: 16 }}
        onClick={() => navigate("/payroll")}
      >
        <I.chevron size={14} style={{ transform: "rotate(180deg)" }} /> Back to Payroll
      </Button>
      <Card>
        <div style={{ padding: 28 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
            }}
          >
            <div>
              <span className="eyebrow">{period.code}</span>
              <h1 style={{ fontSize: 36, color: "var(--ink-3)", margin: "8px 0" }}>
                {period.name} payroll
              </h1>
              <div
                style={{
                  display: "flex",
                  gap: 14,
                  fontSize: 13,
                  color: "var(--text-2)",
                  marginTop: 6,
                }}
              >
                <span>
                  <I.calendar size={13} /> Cut-off {period.end_date}
                </span>
                <span>
                  <I.money size={13} /> Pay date {period.pay_date}
                </span>
                <span>
                  <I.users size={13} /> {period.record_count ?? records.length} record
                  {(period.record_count ?? records.length) === 1 ? "" : "s"}
                </span>
              </div>
            </div>
            <StatusBadge status={period.status_display || period.status} />
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 24,
              marginTop: 28,
              padding: "20px 0",
              borderTop: "1px solid var(--hairline-2)",
              borderBottom: "1px solid var(--hairline-2)",
            }}
          >
            {[
              { l: "Gross", v: moneyOf(String(totals.gross)) },
              { l: "Allowances", v: moneyOf(String(totals.allowances)) },
              { l: "Deductions", v: moneyOf(String(totals.deductions)) },
              { l: "Net", v: moneyOf(String(totals.net)) },
            ].map((m) => (
              <div key={m.l}>
                <div className="eyebrow">{m.l}</div>
                <div style={{ fontSize: 30, color: "var(--ink-3)", marginTop: 4 }}>{m.v}</div>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", gap: 6, marginTop: 20, flexWrap: "wrap" }}>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={downloadBankFile}
              disabled={records.length === 0}
              title={
                records.length === 0
                  ? "Generate records first — there's nothing to export yet."
                  : `Download ${records.length} row${records.length === 1 ? "" : "s"} as CSV`
              }
            >
              Bank file (.csv)
            </Button>
            {!isApproved && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.check size={14} />}
                onClick={() => approve.mutate()}
                disabled={approve.isPending}
              >
                {approve.isPending ? "Approving…" : "Approve run"}
              </Button>
            )}
            {isApproved && !isPaid && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.money size={14} />}
                onClick={() => markPaid.mutate()}
                disabled={markPaid.isPending}
              >
                {markPaid.isPending ? "Marking…" : "Mark as paid"}
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.send size={14} />}
              onClick={() => publish.mutate()}
              disabled={publish.isPending || !isApproved}
              title={isApproved ? "Generate + publish payslips" : "Approve the period first"}
            >
              {publish.isPending ? "Publishing…" : "Publish payslips"}
            </Button>
          </div>
        </div>
      </Card>

      <Card style={{ marginTop: 20 }}>
        <CardHead title="Approval flow" />
        <div className="card-body">
          <ApprovalTimeline
            nodes={[
              {
                who: "Records generated",
                when: period.created_at ? new Date(period.created_at).toLocaleDateString() : "",
                what: `${period.record_count ?? records.length} record(s) in this period`,
                state: "done",
              },
              {
                who: "Run approved",
                when: period.approved_at
                  ? new Date(period.approved_at).toLocaleDateString()
                  : "Awaiting",
                state: isApproved ? "done" : "active",
              },
              {
                who: "Payment released",
                when: isPaid ? "Released" : "On approval",
                state: isPaid ? "done" : "",
              },
            ]}
          />
        </div>
      </Card>

      <Card style={{ marginTop: 20 }}>
        <CardHead title="Records" sub={`${records.length} per-employee row${records.length === 1 ? "" : "s"}`} />
        {recordsQ.isLoading ? (
          <div className="card-body" style={{ color: "var(--text-3)" }}>Loading…</div>
        ) : records.length === 0 ? (
          <div className="empty" style={{ margin: 16 }}>
            <div className="title">No records yet</div>
            <div className="lede">
              Generate records from this period by re-running it from the list page.
            </div>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Basic</th>
                <th>Allowances</th>
                <th>Deductions</th>
                <th>Net</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {records.slice(0, 50).map((r) => (
                <tr key={r.id}>
                  <td>{r.employee_name || "—"}</td>
                  <td className="num">{moneyOf(r.basic_salary)}</td>
                  <td className="num">{moneyOf(r.total_allowances)}</td>
                  <td className="num">{moneyOf(r.total_deductions)}</td>
                  <td className="num" style={{ fontWeight: 600 }}>
                    {moneyOf(r.net_pay)}
                  </td>
                  <td>
                    <StatusBadge status={r.status_display || r.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
