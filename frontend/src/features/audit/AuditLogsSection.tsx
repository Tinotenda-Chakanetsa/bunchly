/* Audit logs — backend-driven via /audit/. */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Badge,
  Button,
  Card,
  KpiCell,
  KpiStrip,
  PageHeader,
  Pagination,
  PersonCell,
  useToast,
  usePaginated,
} from "@/components/ui";
import { downloadBlob, downloadCsv, generatePlaceholderPdf } from "@/lib/export";
import { listAuditLog } from "@/api/hr";

export function AuditLogsPage() {
  const toast = useToast();
  const [actorFilter, setActorFilter] = useState("all");
  const [actionFilter, setActionFilter] = useState("all");

  const logs = useQuery({
    queryKey: ["audit-log"],
    queryFn: () => listAuditLog({ page: 1 }),
  });
  const rows = logs.data?.results ?? [];

  const actors = useMemo(() => {
    const m = new Map<string, string>();
    for (const r of rows) {
      const key = r.actor || "system";
      if (!m.has(key)) m.set(key, r.actor_name || "System");
    }
    return Array.from(m.entries());
  }, [rows]);

  const actions = useMemo(
    () => Array.from(new Set(rows.map((r) => r.action))).sort(),
    [rows],
  );

  const filtered = useMemo(() => {
    return rows.filter((r) => {
      if (actorFilter !== "all" && (r.actor || "system") !== actorFilter) return false;
      if (actionFilter !== "all" && r.action !== actionFilter) return false;
      return true;
    });
  }, [rows, actorFilter, actionFilter]);

  const pag = usePaginated(filtered);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Compliance · forensics"
        title="Audit logs"
        lede={
          logs.isLoading
            ? "Loading…"
            : `${logs.data?.count ?? rows.length} events captured`
        }
        actions={
          <Button
            variant="primary"
            size="sm"
            leftIcon={<I.download size={14} />}
            onClick={() => downloadCsv("audit-log.csv", filtered)}
          >
            Export
          </Button>
        }
      />
      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="Events" value={logs.data?.count ?? rows.length} />
        <KpiCell label="Unique actors" value={actors.length} />
        <KpiCell
          label="Sensitive actions"
          value={rows.filter((r) => /salary|bank|id|payroll|sensitive/i.test(r.action || r.entity_type)).length}
        />
        <KpiCell label="Retention" value="7 yrs" sub="Then anonymised" />
      </KpiStrip>
      <Card>
        <div className="table-toolbar">
          <select
            className="select"
            style={{ height: 34, width: 200 }}
            value={actorFilter}
            onChange={(e) => setActorFilter(e.target.value)}
          >
            <option value="all">All users</option>
            {actors.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
          <select
            className="select"
            style={{ height: 34, width: 200 }}
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
          >
            <option value="all">All actions</option>
            {actions.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <Button
            variant="outline"
            size="sm"
            leftIcon={<I.download size={13} />}
            onClick={() => {
              downloadBlob(
                generatePlaceholderPdf(
                  "Audit log export",
                  filtered
                    .slice(0, 30)
                    .map(
                      (l) =>
                        `${l.created_at} · ${l.actor_name || "System"} · ${l.action} · ${l.entity_type}`,
                    ),
                ),
                "audit-log.pdf",
              );
              toast.push("Audit log PDF downloaded", "success");
            }}
          >
            Download PDF
          </Button>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Entity</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {pag.slice.map((a) => (
              <tr key={a.id}>
                <td className="muted num" style={{ fontSize: 12, fontFamily: "var(--mono)" }}>
                  {a.created_at?.replace("T", " ").slice(0, 19) || "—"}
                </td>
                <td>
                  {!a.actor ? (
                    <Badge tone="ink">System</Badge>
                  ) : (
                    <PersonCell name={a.actor_name || "—"} size="sm" />
                  )}
                </td>
                <td>{a.action}</td>
                <td style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--action)" }}>
                  {a.entity_type}
                  {a.entity_id ? <span style={{ color: "var(--text-3)" }}> · {a.entity_id.toString().slice(0, 8)}</span> : null}
                </td>
                <td className="muted" style={{ fontFamily: "var(--mono)", fontSize: 12 }}>
                  {a.ip_address || "—"}
                </td>
              </tr>
            ))}
            {rows.length === 0 && logs.isFetched && (
              <tr>
                <td colSpan={5}>
                  <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                    No audit events captured yet.
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
    </div>
  );
}
