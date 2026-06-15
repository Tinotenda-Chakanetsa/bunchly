/* Employee self-service payslips.
 *
 * Backs onto `/payslips/my-payslips/` — open to every authenticated
 * tenant member who has an Employee profile. The page renders the
 * snapshot the backend freezes at publish time, so payslips remain
 * accurate even if salary / allowance config later changes. */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Button,
  Card,
  CardHead,
  KpiCell,
  KpiStrip,
  Modal,
  PageHeader,
} from "@/components/ui";
import { downloadCsv } from "@/lib/export";
import { listMyPayslips, type Payslip } from "@/api/payroll";

interface SnapshotLine {
  description: string;
  amount: string;
}
interface PayslipSnapshot {
  employee?: string;
  employee_number?: string;
  period?: string;
  currency?: string;
  basic_salary?: string;
  allowances?: SnapshotLine[];
  deductions?: SnapshotLine[];
  overtime_amount?: string;
  leave_without_pay_days?: string;
  leave_without_pay_amount?: string;
  gross_pay?: string;
  net_pay?: string;
}

function snapshot(p: Payslip): PayslipSnapshot {
  return (p.snapshot as PayslipSnapshot | undefined) ?? {};
}

function money(currency: string | undefined, amount: string | undefined): string {
  if (amount === undefined || amount === null || amount === "") return "—";
  const n = Number(amount);
  if (!Number.isFinite(n)) return amount;
  return `${currency ? currency + " " : ""}${n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString();
}

function PayslipDetailModal({
  open,
  onClose,
  payslip,
}: {
  open: boolean;
  onClose: () => void;
  payslip: Payslip | null;
}) {
  if (!payslip) return null;
  const slip = payslip; // narrow once so the closure below keeps the type
  const s = snapshot(slip);
  const allowances = s.allowances ?? [];
  const deductions = s.deductions ?? [];

  function downloadAsCsv() {
    const rows = [
      { line: "Basic salary", amount: s.basic_salary || "0" },
      { line: "Overtime", amount: s.overtime_amount || "0" },
      ...allowances.map((a) => ({ line: a.description, amount: a.amount })),
      ...deductions.map((d) => ({ line: `-${d.description}`, amount: d.amount })),
      {
        line: `Leave without pay (${s.leave_without_pay_days || 0} days)`,
        amount: `-${s.leave_without_pay_amount || "0"}`,
      },
      { line: "Gross pay", amount: s.gross_pay || "0" },
      { line: "Net pay", amount: s.net_pay || "0" },
    ];
    downloadCsv(`payslip-${slip.reference || slip.id}.csv`, rows);
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      width={640}
      title={`Payslip · ${payslip.period_name || s.period || "—"}`}
      sub={`Reference ${payslip.reference} · paid ${fmtDate(payslip.published_at)}`}
      footer={
        <>
          <Button
            variant="outline"
            leftIcon={<I.download size={14} />}
            onClick={downloadAsCsv}
          >
            Download CSV
          </Button>
          <Button variant="primary" onClick={onClose}>
            Close
          </Button>
        </>
      }
    >
      <div className="col" style={{ gap: 14 }}>
        <Card>
          <div
            style={{
              padding: 18,
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 11,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--text-3)",
                  fontWeight: 600,
                }}
              >
                Net pay
              </div>
              <div
                style={{
                  fontSize: 32,
                  fontWeight: 600,
                  color: "var(--ink-3)",
                  marginTop: 4,
                }}
              >
                {money(s.currency, s.net_pay)}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 2 }}>
                Gross {money(s.currency, s.gross_pay)}
              </div>
            </div>
            <div style={{ fontSize: 12.5, color: "var(--text-2)" }}>
              <div>
                <strong>{s.employee}</strong>
              </div>
              <div>Number {s.employee_number}</div>
              <div>Period {s.period}</div>
            </div>
          </div>
        </Card>

        <Card>
          <CardHead title="Earnings" />
          <table className="table">
            <tbody>
              <tr>
                <td>Basic salary</td>
                <td className="num">{money(s.currency, s.basic_salary)}</td>
              </tr>
              {Number(s.overtime_amount || 0) > 0 && (
                <tr>
                  <td>Overtime</td>
                  <td className="num">{money(s.currency, s.overtime_amount)}</td>
                </tr>
              )}
              {allowances.map((a, i) => (
                <tr key={`a-${i}`}>
                  <td>{a.description}</td>
                  <td className="num">{money(s.currency, a.amount)}</td>
                </tr>
              ))}
              {allowances.length === 0 && Number(s.overtime_amount || 0) === 0 && (
                <tr>
                  <td colSpan={2} className="muted" style={{ textAlign: "center" }}>
                    No additional earnings this period
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>

        <Card>
          <CardHead title="Deductions" />
          <table className="table">
            <tbody>
              {deductions.map((d, i) => (
                <tr key={`d-${i}`}>
                  <td>{d.description}</td>
                  <td className="num">−{money(s.currency, d.amount)}</td>
                </tr>
              ))}
              {Number(s.leave_without_pay_amount || 0) > 0 && (
                <tr>
                  <td>
                    Leave without pay ({s.leave_without_pay_days || 0} days)
                  </td>
                  <td className="num">
                    −{money(s.currency, s.leave_without_pay_amount)}
                  </td>
                </tr>
              )}
              {deductions.length === 0 &&
                Number(s.leave_without_pay_amount || 0) === 0 && (
                  <tr>
                    <td
                      colSpan={2}
                      className="muted"
                      style={{ textAlign: "center" }}
                    >
                      No deductions this period
                    </td>
                  </tr>
                )}
            </tbody>
          </table>
        </Card>
      </div>
    </Modal>
  );
}

export default function MyPayslipsPage() {
  const payslipsQ = useQuery({
    queryKey: ["my-payslips"],
    queryFn: listMyPayslips,
  });
  const [selected, setSelected] = useState<Payslip | null>(null);

  const payslips = payslipsQ.data ?? [];

  const stats = useMemo(() => {
    const totalNet = payslips.reduce(
      (sum, p) => sum + Number(snapshot(p).net_pay || 0),
      0,
    );
    const totalGross = payslips.reduce(
      (sum, p) => sum + Number(snapshot(p).gross_pay || 0),
      0,
    );
    const currency = payslips.length > 0 ? snapshot(payslips[0]).currency : "";
    return { totalNet, totalGross, currency, count: payslips.length };
  }, [payslips]);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Your earnings"
        title="My payslips"
        lede={
          payslipsQ.isLoading
            ? "Loading…"
            : payslips.length === 0
              ? "No payslips yet — they'll appear here once payroll publishes them."
              : `${payslips.length} payslip${payslips.length === 1 ? "" : "s"} on file`
        }
      />

      {payslips.length > 0 && (
        <KpiStrip cols={3} style={{ marginBottom: 20 }}>
          <KpiCell label="Payslips" value={stats.count} />
          <KpiCell
            label="Total gross"
            value={money(stats.currency, String(stats.totalGross))}
          />
          <KpiCell
            label="Total net"
            value={money(stats.currency, String(stats.totalNet))}
          />
        </KpiStrip>
      )}

      <Card>
        <CardHead
          title="Payslip history"
          sub="Click any row to open the detailed breakdown"
        />
        {payslipsQ.isLoading ? (
          <div className="card-body" style={{ color: "var(--text-3)" }}>
            Loading…
          </div>
        ) : payslips.length === 0 ? (
          <div className="empty" style={{ margin: 16 }}>
            <div className="title">No payslips published yet</div>
            <div className="lede">
              When your employer publishes a payslip for you it will show up
              here. You'll also get a notification.
            </div>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Period</th>
                <th>Reference</th>
                <th>Paid on</th>
                <th>Gross</th>
                <th>Net</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {payslips.map((p) => {
                const s = snapshot(p);
                return (
                  <tr
                    key={p.id}
                    className="clickable"
                    onClick={() => setSelected(p)}
                  >
                    <td>
                      <div style={{ fontWeight: 600 }}>
                        {p.period_name || s.period || "—"}
                      </div>
                    </td>
                    <td className="muted">{p.reference}</td>
                    <td className="muted num">{fmtDate(p.published_at)}</td>
                    <td className="num">{money(s.currency, s.gross_pay)}</td>
                    <td className="num" style={{ fontWeight: 600 }}>
                      {money(s.currency, s.net_pay)}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <I.chevron size={14} style={{ color: "var(--text-3)" }} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>

      <PayslipDetailModal
        open={!!selected}
        onClose={() => setSelected(null)}
        payslip={selected}
      />
    </div>
  );
}
