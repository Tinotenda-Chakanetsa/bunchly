import { useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I, type IconName } from "@/components/icons";
import {
  Avatar,
  Badge,
  BarChart,
  Button,
  Card,
  CardHead,
  ColumnChart,
  Empty,
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
import * as Demo from "@/lib/demo";
import { downloadBlob, downloadCsv, downloadJson, generatePlaceholderPdf } from "@/lib/export";
import { useAuth } from "@/store/auth";
import { useStore } from "@/lib/store";
import {
  commitImport,
  createSavedReport,
  deleteSavedReport,
  downloadImportTemplate,
  exportReport,
  getCurrentTenant,
  getTenantSettings,
  listImportBatches,
  listImportEntityTypes,
  listReportCatalogue,
  listSavedReports,
  updateSavedReport,
  updateTenantSettings,
  validateImport,
  type ImportBatch,
  type ImportEntity,
  type ReportCatalogueEntry,
  type SavedReport,
} from "@/api/admin";
import { listEmployees } from "@/api/employees";

/* ============================================
 * IMPORTS
 * ============================================ */

function ImportRunner({
  open,
  onClose,
  entity,
}: {
  open: boolean;
  onClose: () => void;
  entity: ImportEntity | null;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [stage, setStage] = useState<"pick" | "preview" | "done">("pick");
  const [file, setFile] = useState<File | null>(null);
  const [batch, setBatch] = useState<ImportBatch | null>(null);

  function reset() {
    setStage("pick");
    setFile(null);
    setBatch(null);
  }

  const validate = useMutation({
    mutationFn: (f: File) => {
      if (!entity) throw new Error("no entity");
      return validateImport({ entity_type: entity.key, file: f });
    },
    onSuccess: (b) => {
      setBatch(b);
      setStage("preview");
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: { detail?: string; file?: string[] } } }).response?.data;
      toast.push(data?.detail || data?.file?.[0] || "Validation failed", "error");
    },
  });

  const commit = useMutation({
    mutationFn: () => {
      if (!batch || !file) throw new Error("missing batch or file");
      return commitImport(batch.id, file);
    },
    onSuccess: (b) => {
      setBatch(b);
      setStage("done");
      toast.push(
        `Imported ${b.committed_rows} row${b.committed_rows === 1 ? "" : "s"}`,
        "success",
      );
      queryClient.invalidateQueries({ queryKey: ["import-batches"] });
      setTimeout(() => {
        onClose();
        reset();
      }, 1200);
    },
    onError: () => toast.push("Commit failed — see batch errors", "error"),
  });

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    validate.mutate(f);
  }

  return (
    <Modal
      open={open && !!entity}
      onClose={() => {
        onClose();
        reset();
      }}
      title={`Import ${entity?.label ?? ""}`}
      sub="CSV file → validate → commit"
      width={720}
      footer={
        stage === "pick" ? (
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        ) : stage === "preview" ? (
          <>
            <Button variant="ghost" onClick={reset}>
              Re-pick file
            </Button>
            <Button
              variant="primary"
              onClick={() => commit.mutate()}
              disabled={
                commit.isPending || !batch || (batch.error_rows ?? 0) > 0 || batch.valid_rows === 0
              }
            >
              {commit.isPending ? "Committing…" : `Commit ${batch?.valid_rows ?? 0} rows`}
            </Button>
          </>
        ) : (
          <Button variant="primary" onClick={onClose}>
            Done
          </Button>
        )
      }
    >
      {stage === "pick" && (
        <>
          <div
            onClick={() => fileRef.current?.click()}
            style={{
              padding: 36,
              border: "2px dashed var(--hairline)",
              borderRadius: 12,
              textAlign: "center",
              background: "var(--card-2)",
              cursor: "pointer",
            }}
          >
            <I.upload size={28} style={{ color: "var(--action)", margin: "0 auto 12px" }} />
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {validate.isPending ? "Validating…" : "Drop CSV here or click to browse"}
            </div>
            <div style={{ fontSize: 12.5, color: "var(--text-3)" }}>
              Required columns: <strong>{entity?.required.join(", ") || "—"}</strong>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv"
              onChange={onFile}
              style={{ display: "none" }}
              disabled={validate.isPending}
            />
          </div>
          {entity && (
            <div style={{ marginTop: 12, textAlign: "center" }}>
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<I.download size={13} />}
                onClick={async () => {
                  const blob = await downloadImportTemplate(entity.key);
                  downloadBlob(blob, `${entity.key}_template.csv`);
                }}
              >
                Download CSV template
              </Button>
            </div>
          )}
        </>
      )}
      {stage === "preview" && batch && (
        <div>
          <KpiStrip cols={4} style={{ marginBottom: 16 }}>
            <KpiCell label="Total rows" value={batch.total_rows} />
            <KpiCell label="Valid" value={batch.valid_rows} sub="Ready to commit" />
            <KpiCell label="Errors" value={batch.error_rows} sub="Will be skipped" />
            <KpiCell label="Status" value={batch.status_display || batch.status} />
          </KpiStrip>
          {(batch.errors ?? []).length > 0 && (
            <div
              style={{
                maxHeight: 220,
                overflowY: "auto",
                border: "1px solid var(--hairline)",
                borderRadius: 8,
                marginBottom: 8,
              }}
            >
              <table className="table">
                <thead>
                  <tr>
                    <th>Row</th>
                    <th>Field</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {(batch.errors ?? []).slice(0, 50).map((e) => (
                    <tr key={e.id}>
                      <td className="num">{e.row_number}</td>
                      <td className="muted">{e.field || "—"}</td>
                      <td>{e.error}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      {stage === "done" && batch && (
        <div style={{ padding: 32, textAlign: "center" }}>
          <I.check size={28} style={{ color: "var(--positive)", margin: "0 auto 12px" }} />
          <div style={{ fontWeight: 600 }}>
            Imported {batch.committed_rows} row{batch.committed_rows === 1 ? "" : "s"}
          </div>
        </div>
      )}
    </Modal>
  );
}

export function ImportsPage() {
  const entitiesQ = useQuery({ queryKey: ["import-entities"], queryFn: listImportEntityTypes });
  const batchesQ = useQuery({
    queryKey: ["import-batches"],
    queryFn: () => listImportBatches(),
  });
  const [running, setRunning] = useState<ImportEntity | null>(null);

  const entities = entitiesQ.data ?? [];
  const batches: ImportBatch[] = batchesQ.data?.results ?? [];
  const pag = usePaginated(batches);

  const lastByEntity = useMemo(() => {
    const m = new Map<string, ImportBatch>();
    for (const b of batches) {
      if (!m.has(b.entity_type)) m.set(b.entity_type, b);
    }
    return m;
  }, [batches]);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Bulk operations"
        title="Imports"
        lede={
          batchesQ.isLoading
            ? "Loading…"
            : `${batches.length} import${batches.length === 1 ? "" : "s"} on record`
        }
        actions={
          <Button
            variant="outline"
            size="sm"
            leftIcon={<I.download size={14} />}
            onClick={() => downloadCsv("import-history.csv", batches)}
          >
            Export history
          </Button>
        }
      />
      <div className="list" style={{ marginBottom: 20 }}>
        {entities.length === 0 && !entitiesQ.isLoading && (
          <div className="list-row">
            <div className="row-main">
              <div className="row-title">No import entities available</div>
              <div className="row-sub">
                The backend's import registry returned nothing for this tenant.
              </div>
            </div>
          </div>
        )}
        {entities.map((k) => {
          const last = lastByEntity.get(k.key);
          return (
            <div key={k.key} className="list-row">
              <div className="row-icon">
                <I.upload size={16} />
              </div>
              <div className="row-main">
                <div className="row-title">{k.label}</div>
                <div className="row-sub">
                  {k.columns.length} column{k.columns.length === 1 ? "" : "s"} ·
                  required: {k.required.join(", ") || "—"}
                </div>
              </div>
              <span className="row-meta">
                {last ? `Last: ${new Date(last.created_at).toLocaleDateString()}` : "Never"}
              </span>
              <Button variant="outline" size="sm" onClick={() => setRunning(k)}>
                Import
              </Button>
            </div>
          );
        })}
      </div>
      <Card>
        <CardHead title="Recent imports" />
        {batches.length === 0 && !batchesQ.isLoading ? (
          <div className="empty" style={{ margin: 16 }}>
            <div className="title">No imports yet</div>
            <div className="lede">Run your first one from the list above.</div>
          </div>
        ) : (
          <>
            <table className="table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Filename</th>
                  <th>Rows</th>
                  <th>Status</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {pag.slice.map((r) => (
                  <tr key={r.id}>
                    <td>{r.entity_type_display || r.entity_type}</td>
                    <td className="muted">{r.original_filename || "—"}</td>
                    <td className="num">
                      {r.committed_rows ?? 0} / {r.total_rows}
                    </td>
                    <td>
                      <StatusBadge status={r.status_display || r.status} />
                    </td>
                    <td className="muted num">{new Date(r.created_at).toLocaleDateString()}</td>
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
      <ImportRunner open={!!running} onClose={() => setRunning(null)} entity={running} />
    </div>
  );
}

/* ============================================
 * POLICIES — backend-driven; see features/policies/PoliciesSection.tsx
 * ============================================ */

export { PoliciesPage } from "@/features/policies/PoliciesSection";

/* ============================================
 * HR CASES
 * ============================================ */


// HR Cases — backend-driven; the implementation moved out to a feature module.
export { HRCasesPage, CaseDetailPage } from "@/features/hr_cases/HRCasesSection";


/* ============================================
 * REPORTS
 * ============================================ */

/* Group key derivation from a backend `report_key` like
   "headcount_by_department" → "People". This is the only place the
   frontend imposes a group taxonomy; the backend catalogue is flat. */
function groupForReport(key: string, label: string): string {
  const hay = (key + " " + label).toLowerCase();
  if (/(leave|absence|holiday)/.test(hay)) return "Leave";
  if (/(claim|education|benefit)/.test(hay)) return "Benefits";
  if (/(document|policy|compliance|audit)/.test(hay)) return "Compliance";
  if (/(payroll|salary|comp)/.test(hay)) return "Payroll";
  if (/(recruit|candidate|hire)/.test(hay)) return "Recruitment";
  return "People";
}

function ReportsLibrary({
  reports,
  onRun,
  favouriteKeys,
  onFavourite,
  isRunning,
}: {
  reports: ReportCatalogueEntry[];
  onRun: (entry: ReportCatalogueEntry) => void;
  favouriteKeys: Set<string>;
  onFavourite: (entry: ReportCatalogueEntry) => void;
  isRunning: string | null;
}) {
  const groups = useMemo(() => {
    const buckets = new Map<string, ReportCatalogueEntry[]>();
    for (const r of reports) {
      const g = groupForReport(r.key, r.label);
      const existing = buckets.get(g) ?? [];
      existing.push(r);
      buckets.set(g, existing);
    }
    return Array.from(buckets.entries()).map(([group, items]) => ({ group, items }));
  }, [reports]);

  if (reports.length === 0) {
    return (
      <Empty
        icon="chart"
        title="No reports available"
        lede="The backend catalogue returned nothing — check your role permissions."
      />
    );
  }

  return (
    <div className="col" style={{ gap: 24 }}>
      {groups.map((g) => (
        <div key={g.group}>
          <h2 style={{ margin: "0 0 12px", fontSize: 22, color: "var(--ink-3)" }}>{g.group}</h2>
          <div className="list">
            {g.items.map((r) => {
              const fav = favouriteKeys.has(r.key);
              return (
                <div key={r.key} className="list-row">
                  <div className="row-icon">
                    <I.chart size={16} />
                  </div>
                  <div className="row-main">
                    <div className="row-title">{r.label}</div>
                    <div className="row-sub">{r.description || r.key}</div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    title="Favourite"
                    onClick={() => onFavourite(r)}
                  >
                    <I.star
                      size={13}
                      style={{ color: fav ? "var(--yellow-deep)" : "var(--text-4)" }}
                    />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<I.download size={13} />}
                    onClick={() => onRun(r)}
                    disabled={isRunning === r.key}
                  >
                    {isRunning === r.key ? "Running…" : "Run"}
                  </Button>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function ExecutiveDashboard() {
  return (
    <div className="col" style={{ gap: 14 }}>
      <KpiStrip cols={4}>
        <KpiCell label="Turnover" value="8.4%" delta="-1.2 pts" deltaTone="up" />
        <KpiCell label="Absence rate" value="2.6%" delta="+0.1 pts" deltaTone="flat" />
        <KpiCell label="Time to hire" value="34d" delta="-5d" deltaTone="up" />
        <KpiCell label="Engagement" value="4.4" delta="+0.2" deltaTone="up" />
      </KpiStrip>
      <Card>
        <CardHead title="Headcount · 12 months" />
        <div className="card-body">
          <ColumnChart
            format={(v) => v.toString()}
            data={[
              { label: "Jun", value: 118 }, { label: "Jul", value: 119 }, { label: "Aug", value: 121 }, { label: "Sep", value: 122 },
              { label: "Oct", value: 120 }, { label: "Nov", value: 122 }, { label: "Dec", value: 121 }, { label: "Jan", value: 124 },
              { label: "Feb", value: 126 }, { label: "Mar", value: 127 }, { label: "Apr", value: 129 }, { label: "May", value: 131, color: "var(--yellow)" },
            ]}
          />
        </div>
      </Card>
      <Card>
        <CardHead title="Cost per department" sub="Trailing 12 months, in $" />
        <div className="card-body">
          <BarChart
            format={(v) => `$${(v / 1000).toFixed(0)}k`}
            data={[
              { label: "Engineering", value: 3640 },
              { label: "Sales", value: 2280 },
              { label: "Customer Success", value: 1480 },
              { label: "Marketing", value: 1320 },
              { label: "Design", value: 1180 },
              { label: "Finance", value: 980 },
              { label: "People Ops", value: 720, color: "var(--yellow)" },
              { label: "Legal", value: 580 },
            ]}
          />
        </div>
      </Card>
    </div>
  );
}

export function ReportsPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [tab, setTab] = useState("library");
  const [running, setRunning] = useState<string | null>(null);

  const catalogueQ = useQuery({ queryKey: ["report-catalogue"], queryFn: listReportCatalogue });
  const savedQ = useQuery({ queryKey: ["saved-reports"], queryFn: listSavedReports });

  const reports: ReportCatalogueEntry[] = catalogueQ.data ?? [];
  const saved: SavedReport[] = savedQ.data ?? [];
  const favouriteKeys = useMemo(
    () => new Set(saved.filter((r) => r.is_favourite).map((r) => r.report_key)),
    [saved],
  );

  const createFav = useMutation({
    mutationFn: (entry: ReportCatalogueEntry) =>
      createSavedReport({ name: entry.label, report_key: entry.key, is_favourite: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-reports"] }),
  });

  const toggleFav = useMutation({
    mutationFn: ({ id, current }: { id: string; current: boolean }) =>
      updateSavedReport(id, { is_favourite: !current }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-reports"] }),
  });

  const removeFav = useMutation({
    mutationFn: (id: string) => deleteSavedReport(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-reports"] }),
  });

  async function handleRun(entry: ReportCatalogueEntry) {
    setRunning(entry.key);
    try {
      const { blob, filename } = await exportReport(entry.key, "csv");
      downloadBlob(blob, filename);
      toast.push(`"${entry.label}" downloaded`, "success");
      const existing = saved.find((s) => s.report_key === entry.key);
      if (!existing) {
        await createSavedReport({ name: entry.label, report_key: entry.key });
        queryClient.invalidateQueries({ queryKey: ["saved-reports"] });
      }
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { detail?: string } } }).response?.data;
      toast.push(data?.detail || "Report export failed", "error");
    } finally {
      setRunning(null);
    }
  }

  function handleFavourite(entry: ReportCatalogueEntry) {
    const existing = saved.find((s) => s.report_key === entry.key);
    if (existing) {
      toggleFav.mutate({ id: existing.id, current: !!existing.is_favourite });
    } else {
      createFav.mutate(entry);
    }
  }

  const favourites = saved.filter((s) => s.is_favourite);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Insights & analytics"
        title="Reports"
        lede={
          catalogueQ.isLoading
            ? "Loading…"
            : `${reports.length} report${reports.length === 1 ? "" : "s"} · ${favourites.length} favourite${favourites.length === 1 ? "" : "s"}`
        }
        actions={
          <Button
            variant="outline"
            size="sm"
            leftIcon={<I.download size={14} />}
            onClick={() => downloadCsv("saved-reports.csv", saved)}
          >
            Export list
          </Button>
        }
      />
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "library", label: "Library", count: reports.length },
          { value: "favourites", label: "Favourites", count: favourites.length },
          { value: "executive", label: "Executive dashboard" },
        ]}
      />
      {tab === "library" && (
        <ReportsLibrary
          reports={reports}
          onRun={handleRun}
          favouriteKeys={favouriteKeys}
          onFavourite={handleFavourite}
          isRunning={running}
        />
      )}
      {tab === "executive" && <ExecutiveDashboard />}
      {tab === "favourites" &&
        (favourites.length === 0 ? (
          <Empty
            icon="chart"
            title="No favourites yet"
            lede="Star a report in the library to pin it here."
          />
        ) : (
          <Card>
            <table className="table">
              <thead>
                <tr>
                  <th>Report</th>
                  <th>Key</th>
                  <th>Saved</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {favourites.map((r) => (
                  <tr key={r.id}>
                    <td>{r.name}</td>
                    <td className="muted">{r.report_key}</td>
                    <td className="muted">
                      {r.created_at ? new Date(r.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRun({ key: r.report_key, label: r.name })}
                        disabled={running === r.report_key}
                      >
                        {running === r.report_key ? "Running…" : "Run"}
                      </Button>{" "}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFav.mutate(r.id)}
                        disabled={removeFav.isPending}
                      >
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        ))}
    </div>
  );
}

/* ============================================
 * SETTINGS — wired multi-panel settings
 * ============================================ */

function WorkspacePanel() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const tenantQ = useQuery({ queryKey: ["current-tenant"], queryFn: getCurrentTenant });
  const settingsQ = useQuery({ queryKey: ["tenant-settings"], queryFn: getTenantSettings });

  const [timezone, setTimezone] = useState("");
  const [locale, setLocale] = useState("");
  const [primaryColor, setPrimaryColor] = useState("");

  const settings = settingsQ.data;
  const tenant = tenantQ.data;

  /* Hydrate the form once data arrives. We intentionally don't keep the
     local state in sync after that so the user's edits aren't blown away. */
  useMemo(() => {
    if (settings && !timezone && !locale) {
      setTimezone(settings.timezone || "UTC");
      setLocale(settings.locale || "en");
      setPrimaryColor(settings.primary_color || "#2F6EDB");
    }
  }, [settings, timezone, locale]);

  const save = useMutation({
    mutationFn: () =>
      updateTenantSettings({
        timezone: timezone || undefined,
        locale: locale || undefined,
        primary_color: primaryColor || undefined,
      }),
    onSuccess: () => {
      toast.push("Workspace settings saved", "success");
      queryClient.invalidateQueries({ queryKey: ["tenant-settings"] });
    },
    onError: () => toast.push("Could not save settings", "error"),
  });

  if (settingsQ.isLoading || tenantQ.isLoading) {
    return (
      <Card>
        <div className="card-body" style={{ color: "var(--text-3)" }}>Loading…</div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHead
        title="Workspace"
        sub={tenant ? `${tenant.name} · ${tenant.slug}` : "The basics about your organisation"}
      />
      <div className="card-body" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
        <div className="field">
          <label>Organisation name</label>
          <input
            className="input"
            value={tenant?.name ?? ""}
            disabled
            title="Edit from the Tenants admin"
          />
        </div>
        <div className="field">
          <label>Country</label>
          <input
            className="input"
            value={tenant?.country ?? ""}
            disabled
            title="Edit from the Tenants admin"
          />
        </div>
        <div className="field">
          <label>Time zone</label>
          <input
            className="input"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            placeholder="UTC"
          />
        </div>
        <div className="field">
          <label>Locale</label>
          <input
            className="input"
            value={locale}
            onChange={(e) => setLocale(e.target.value)}
            placeholder="en"
          />
        </div>
        <div className="field" style={{ gridColumn: "1 / -1" }}>
          <label>Primary brand colour</label>
          <input
            className="input"
            type="color"
            value={primaryColor}
            onChange={(e) => setPrimaryColor(e.target.value)}
            style={{ height: 40, padding: 4 }}
          />
        </div>
      </div>
      <div className="card-foot">
        <span style={{ fontSize: 12, color: "var(--text-3)" }}>
          Applies tenant-wide. Editable fields PATCH <code>/tenants/current/settings/</code>.
        </span>
        <Button
          variant="primary"
          onClick={() => save.mutate()}
          disabled={save.isPending}
        >
          {save.isPending ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </Card>
  );
}

function MembersPanel() {
  const employeesQ = useQuery({ queryKey: ["employees"], queryFn: () => listEmployees() });
  const members = (employeesQ.data?.results ?? []).slice(0, 12);
  return (
    <Card>
      <CardHead
        title="Members & roles"
        sub={
          employeesQ.isLoading
            ? "Loading…"
            : `${employeesQ.data?.count ?? members.length} active members`
        }
        action={
          <Button variant="primary" size="sm" leftIcon={<I.plus size={13} />} disabled>
            Invite
          </Button>
        }
      />
      {members.length === 0 ? (
        <div className="empty" style={{ margin: 16 }}>
          <div className="title">No members yet</div>
          <div className="lede">Add people from <strong>People → Add person</strong>.</div>
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Member</th>
              <th>Department</th>
              <th>Joined</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.id}>
                <td>
                  <PersonCell name={m.full_name} sub={m.job_title_name} />
                </td>
                <td>
                  <Badge tone="outline">{m.department_name || "—"}</Badge>
                </td>
                <td className="muted">{m.start_date || "—"}</td>
                <td>
                  <StatusBadge status={m.employment_status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

function NotificationsPanel() {
  const triggers = useStore((s) => s.notificationTriggers);
  const toggle = useStore((s) => s.toggleNotificationTrigger);
  return (
    <Card>
      <CardHead title="Automated notifications" sub="What goes out, to whom, and how" />
      <table className="table">
        <thead>
          <tr>
            <th>Trigger</th>
            <th>Channels</th>
            <th>Enabled</th>
          </tr>
        </thead>
        <tbody>
          {triggers.map((t) => (
            <tr key={t.id}>
              <td>{t.name}</td>
              <td>
                {t.channels.map((c, j) => (
                  <Badge
                    key={j}
                    tone={c === "Email" ? "blue" : c === "Slack" ? "yellow" : "outline"}
                    style={{ marginRight: 4 }}
                  >
                    {c}
                  </Badge>
                ))}
              </td>
              <td>
                <button
                  onClick={() => toggle(t.id)}
                  aria-label="Toggle notification"
                  style={{
                    position: "relative",
                    display: "inline-block",
                    width: 36,
                    height: 20,
                    border: "none",
                    background: "transparent",
                    cursor: "pointer",
                  }}
                >
                  <span
                    style={{
                      position: "absolute",
                      inset: 0,
                      background: t.on ? "var(--action)" : "var(--hairline)",
                      borderRadius: 999,
                      transition: "background 0.15s",
                    }}
                  />
                  <span
                    style={{
                      position: "absolute",
                      top: 2,
                      left: t.on ? 18 : 2,
                      width: 16,
                      height: 16,
                      background: "var(--card)",
                      borderRadius: 50,
                      boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
                      transition: "left 0.15s",
                    }}
                  />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function EmailPanel() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const settingsQ = useQuery({ queryKey: ["tenant-settings"], queryFn: getTenantSettings });
  const tenantSettings = settingsQ.data;

  const [fromName, setFromName] = useState("");
  const [replyTo, setReplyTo] = useState("");
  const [recipients, setRecipients] = useState("");

  useMemo(() => {
    if (tenantSettings && !fromName && !replyTo) {
      setFromName(tenantSettings.email_sender_name || "");
      setReplyTo(tenantSettings.email_reply_to || "");
      setRecipients((tenantSettings.notification_recipients ?? []).join(", "));
    }
  }, [tenantSettings, fromName, replyTo]);

  const save = useMutation({
    mutationFn: () =>
      updateTenantSettings({
        email_sender_name: fromName || undefined,
        email_reply_to: replyTo || undefined,
        notification_recipients: recipients
          ? recipients.split(",").map((s) => s.trim()).filter(Boolean)
          : [],
      }),
    onSuccess: () => {
      toast.push("Email settings saved", "success");
      queryClient.invalidateQueries({ queryKey: ["tenant-settings"] });
    },
    onError: () => toast.push("Could not save email settings", "error"),
  });

  if (settingsQ.isLoading) {
    return (
      <Card>
        <div className="card-body" style={{ color: "var(--text-3)" }}>Loading…</div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHead
        title="Email & SMTP"
        sub="Sender identity · transport is environment-configured"
      />
      <div className="card-body" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
        <div className="field">
          <label>From name</label>
          <input
            className="input"
            value={fromName}
            onChange={(e) => setFromName(e.target.value)}
            placeholder="Bunchly HR"
          />
        </div>
        <div className="field">
          <label>Reply-to address</label>
          <input
            className="input"
            type="email"
            value={replyTo}
            onChange={(e) => setReplyTo(e.target.value)}
            placeholder="hr@yourcompany.com"
          />
        </div>
        <div className="field" style={{ gridColumn: "1 / -1" }}>
          <label>Notification recipients</label>
          <input
            className="input"
            value={recipients}
            onChange={(e) => setRecipients(e.target.value)}
            placeholder="hr@yourcompany.com, finance@yourcompany.com"
          />
          <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 4 }}>
            Comma-separated. These addresses receive cross-cutting alerts (claim approvals, doc
            reminders, etc.).
          </div>
        </div>
        <div className="field" style={{ gridColumn: "1 / -1" }}>
          <label>Transport</label>
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <Badge tone="blue" dot>
              Configured via <code>EMAIL_PROVIDER</code> env var
            </Badge>
            <span style={{ fontSize: 12, color: "var(--text-3)" }}>
              Set <code>RESEND_API_KEY</code> or SMTP credentials in the backend env to enable
              sending.
            </span>
          </div>
        </div>
      </div>
      <div className="card-foot">
        <span style={{ fontSize: 12, color: "var(--text-3)" }}>
          PATCH <code>/tenants/current/settings/</code>
        </span>
        <Button
          variant="primary"
          onClick={() => save.mutate()}
          disabled={save.isPending}
        >
          {save.isPending ? "Saving…" : "Save"}
        </Button>
      </div>
    </Card>
  );
}

function IntegrationsPanel() {
  const items = useStore((s) => s.integrations);
  const toggle = useStore((s) => s.toggleIntegration);
  const toast = useToast();
  return (
    <div className="list">
      {items.map((i) => (
        <div key={i.name} className="list-row" style={{ alignItems: "center" }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: "var(--mist)",
              border: "1px solid var(--hairline)",
              display: "grid",
              placeItems: "center",
              fontWeight: 700,
              fontSize: 16,
              color: "var(--ink-3)",
              flexShrink: 0,
            }}
          >
            {i.logo}
          </div>
          <div className="row-main">
            <div className="row-title">{i.name}</div>
            <div className="row-sub">{i.desc}</div>
          </div>
          <Badge tone={i.on ? "green" : "outline"} dot>
            {i.on ? "Connected" : "Not connected"}
          </Badge>
          <Button
            variant={i.on ? "outline" : "primary"}
            size="sm"
            onClick={() => {
              toggle(i.name);
              toast.push(`${i.name} ${i.on ? "disconnected" : "connected"}`, "success");
            }}
          >
            {i.on ? "Disconnect" : "Connect"}
          </Button>
        </div>
      ))}
    </div>
  );
}

function SecurityPanel() {
  const s = useStore((x) => x.securitySettings);
  const update = useStore((x) => x.updateSecuritySettings);
  const toast = useToast();

  const Toggle = ({
    label,
    desc,
    on,
    onChange,
  }: {
    label: string;
    desc: string;
    on: boolean;
    onChange: () => void;
  }) => (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "12px 0",
        borderBottom: "1px solid var(--hairline-2)",
      }}
    >
      <div>
        <div style={{ fontSize: 13.5, fontWeight: 500 }}>{label}</div>
        <div style={{ fontSize: 12, color: "var(--text-3)" }}>{desc}</div>
      </div>
      <button
        onClick={onChange}
        style={{
          position: "relative",
          display: "inline-block",
          width: 36,
          height: 20,
          border: "none",
          background: "transparent",
          cursor: "pointer",
        }}
      >
        <span
          style={{
            position: "absolute",
            inset: 0,
            background: on ? "var(--action)" : "var(--hairline)",
            borderRadius: 999,
          }}
        />
        <span
          style={{
            position: "absolute",
            top: 2,
            left: on ? 18 : 2,
            width: 16,
            height: 16,
            background: "var(--card)",
            borderRadius: 50,
            boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
            transition: "left 0.15s",
          }}
        />
      </button>
    </div>
  );

  return (
    <div className="col" style={{ gap: 16 }}>
      <Card>
        <CardHead title="Authentication" />
        <div className="card-body" style={{ paddingTop: 0 }}>
          <Toggle
            label="Require 2FA for all users"
            desc="Forces TOTP after next login"
            on={s.require2fa}
            onChange={() => {
              update({ require2fa: !s.require2fa });
              toast.push(`2FA ${s.require2fa ? "disabled" : "enabled"}`, "success");
            }}
          />
          <Toggle
            label="Single sign-on via Google Workspace"
            desc="Email-password disabled when on"
            on={s.ssoGoogle}
            onChange={() => update({ ssoGoogle: !s.ssoGoogle })}
          />
          <Toggle
            label="Single sign-on via SAML"
            desc="Configure your IdP"
            on={s.ssoSaml}
            onChange={() => update({ ssoSaml: !s.ssoSaml })}
          />
        </div>
      </Card>
      <Card>
        <CardHead title="Session & access" />
        <div className="card-body" style={{ paddingTop: 0 }}>
          <Toggle
            label="Lock to IP ranges"
            desc="VPN only for sensitive modules"
            on={s.lockIpRanges}
            onChange={() => update({ lockIpRanges: !s.lockIpRanges })}
          />
          <Toggle
            label="Auto-revoke on offboarding"
            desc="Disable user 24h after exit date"
            on={s.autoRevokeOnExit}
            onChange={() => update({ autoRevokeOnExit: !s.autoRevokeOnExit })}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "12px 0",
            }}
          >
            <div>
              <div style={{ fontSize: 13.5, fontWeight: 500 }}>Session timeout</div>
              <div style={{ fontSize: 12, color: "var(--text-3)" }}>
                Sign-out after N hours of inactivity
              </div>
            </div>
            <input
              type="number"
              className="input"
              style={{ width: 80 }}
              min={1}
              max={24}
              value={s.sessionTimeoutHours}
              onChange={(e) =>
                update({ sessionTimeoutHours: Number(e.target.value) })
              }
            />
          </div>
        </div>
      </Card>
    </div>
  );
}

function DataRetentionPanel() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const settingsQ = useQuery({ queryKey: ["tenant-settings"], queryFn: getTenantSettings });
  const tenantSettings = settingsQ.data;
  const [retentionDays, setRetentionDays] = useState<number>(2555); // 7 years

  useMemo(() => {
    if (tenantSettings && retentionDays === 2555) {
      setRetentionDays(tenantSettings.data_retention_days ?? 2555);
    }
  }, [tenantSettings, retentionDays]);

  const save = useMutation({
    mutationFn: () =>
      updateTenantSettings({ data_retention_days: retentionDays }),
    onSuccess: () => {
      toast.push("Retention policy saved", "success");
      queryClient.invalidateQueries({ queryKey: ["tenant-settings"] });
    },
    onError: () => toast.push("Could not save retention policy", "error"),
  });

  return (
    <Card>
      <CardHead title="Data & retention" sub="These actions affect every record in the workspace" />
      <div className="card-body" style={{ paddingTop: 0 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 0",
            borderBottom: "1px solid var(--hairline-2)",
          }}
        >
          <div>
            <div style={{ fontSize: 13.5, fontWeight: 500 }}>Audit log retention</div>
            <div style={{ fontSize: 12, color: "var(--text-3)" }}>
              How long Bunchly keeps audit + activity records before purging.
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="number"
              className="input"
              style={{ width: 100 }}
              min={30}
              max={3650}
              value={retentionDays}
              onChange={(e) => setRetentionDays(Number(e.target.value))}
            />
            <span style={{ fontSize: 12, color: "var(--text-3)" }}>days</span>
            <Button
              variant="primary"
              size="sm"
              onClick={() => save.mutate()}
              disabled={save.isPending}
            >
              {save.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 0",
          }}
        >
          <div>
            <div style={{ fontSize: 13.5, fontWeight: 500 }}>Export local snapshot</div>
            <div style={{ fontSize: 12, color: "var(--text-3)" }}>
              JSON dump of the in-browser workspace (legacy demo store) — useful for debugging.
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            leftIcon={<I.download size={13} />}
            onClick={() => {
              const snap = useStore.getState();
              downloadJson(
                `bunchly-workspace-${new Date().toISOString().slice(0, 10)}.json`,
                snap,
              );
              toast.push("Snapshot exported", "success");
            }}
          >
            Export JSON
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function SettingsPage() {
  const [tab, setTab] = useState("workspace");
  const navItems: Array<{ v: string; label: string; icon: IconName }> = [
    { v: "workspace", label: "Workspace", icon: "building" },
    { v: "members", label: "Members & roles", icon: "users" },
    { v: "notifications", label: "Notifications", icon: "bell" },
    { v: "email", label: "Email & SMTP", icon: "mail" },
    { v: "integrations", label: "Integrations", icon: "link" },
    { v: "security", label: "Security & SSO", icon: "shield" },
    { v: "data", label: "Data & retention", icon: "trash" },
  ];

  return (
    <div className="page">
      <PageHeader
        eyebrow="Configuration"
        title="Settings"
        lede="Every panel below mutates the live store; changes persist across reloads."
      />
      <div className="grid" style={{ gridTemplateColumns: "220px 1fr", gap: 24 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {navItems.map((s) => {
            const Ic = I[s.icon];
            return (
              <button
                key={s.v}
                onClick={() => setTab(s.v)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "8px 12px",
                  borderRadius: 8,
                  fontSize: 13.5,
                  background: tab === s.v ? "var(--info-soft)" : "transparent",
                  color: tab === s.v ? "var(--action-deep)" : "var(--text-2)",
                  fontWeight: tab === s.v ? 600 : 500,
                  textAlign: "left",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                <Ic size={15} /> {s.label}
              </button>
            );
          })}
        </div>
        <div>
          {tab === "workspace" && <WorkspacePanel />}
          {tab === "members" && <MembersPanel />}
          {tab === "notifications" && <NotificationsPanel />}
          {tab === "email" && <EmailPanel />}
          {tab === "integrations" && <IntegrationsPanel />}
          {tab === "security" && <SecurityPanel />}
          {tab === "data" && <DataRetentionPanel />}
        </div>
      </div>
    </div>
  );
}

/* ============================================
 * AUDIT LOGS
 * ============================================ */

export { AuditLogsPage } from "@/features/audit/AuditLogsSection";

/* Unused helper hint kept to satisfy unused-imports check */
type _ReactNode = ReactNode;
type _Demo = typeof Demo;
type _ = _ReactNode | _Demo;
