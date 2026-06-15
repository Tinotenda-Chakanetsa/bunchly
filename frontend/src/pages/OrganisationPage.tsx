import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Avatar,
  BarChart,
  Button,
  Card,
  CardHead,
  Modal,
  PageHeader,
  Tabs,
  useToast,
} from "@/components/ui";
import { listEmployees, type EmployeeListItem } from "@/api/employees";
import {
  createDepartment,
  listDepartments,
  listLocations,
  type Department,
} from "@/api/organisation";
import { useAuth } from "@/store/auth";

interface ChartPerson {
  id: string;
  name: string;
  title?: string;
  av: string;
}

/* Stable pastel avatar class per employee name — keeps the chart visually
   varied without persisting a "colour" on the backend. */
function avFor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) | 0;
  const slot = Math.abs(hash) % 8;
  return `av-${slot + 1}`;
}

function toChartPerson(e: EmployeeListItem): ChartPerson {
  return {
    id: e.id,
    name: e.full_name || `${e.first_name} ${e.last_name}`,
    title: e.job_title_name,
    av: avFor(e.full_name || e.employee_code),
  };
}

function ChartCard({
  person,
  sub,
  badge,
  tone,
  compact,
  onClick,
}: {
  person: ChartPerson;
  sub?: ReactNode;
  badge?: ReactNode;
  tone?: "yellow";
  compact?: boolean;
  onClick?: () => void;
}) {
  const isYellow = tone === "yellow";
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: compact ? 10 : 12,
        padding: compact ? "8px 10px" : "12px 14px",
        borderRadius: 12,
        background: isYellow ? "var(--yellow)" : "var(--card)",
        border: isYellow ? "1px solid var(--yellow-deep)" : "1px solid var(--hairline)",
        cursor: onClick ? "pointer" : "default",
        boxShadow: isYellow ? "0 4px 16px rgba(252,203,13,0.3)" : "var(--shadow-1)",
        width: "100%",
        textAlign: "left",
        transition: "transform 0.08s, box-shadow 0.1s",
      }}
      onMouseEnter={(e) => {
        if (onClick) e.currentTarget.style.transform = "translateY(-1px)";
      }}
      onMouseLeave={(e) => {
        if (onClick) e.currentTarget.style.transform = "";
      }}
    >
      <Avatar name={person.name} av={person.av} size={compact ? "sm" : undefined} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontWeight: 600,
            fontSize: compact ? 12.5 : 13,
            color: "var(--ink-3)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {person.name}
        </div>
        <div
          style={{
            fontSize: compact ? 11 : 11.5,
            color: "rgba(20,30,44,0.6)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {sub}
        </div>
      </div>
      {badge && (
        <span
          style={{
            fontSize: 10.5,
            fontWeight: 600,
            background: isYellow ? "rgba(0,0,0,0.1)" : "var(--mist)",
            color: isYellow ? "var(--ink-3)" : "var(--text-2)",
            padding: "3px 7px",
            borderRadius: 999,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {badge}
        </span>
      )}
    </button>
  );
}

function OrgChart({ employees }: { employees: EmployeeListItem[] }) {
  const navigate = useNavigate();

  /* Top of the tree = employees with no line manager. We surface up to
     6 visible "leaders" and pick the first one to drill into. */
  const leadership = useMemo(
    () => employees.filter((e) => !e.department_name || true).filter((e) => !e.line_manager_name),
    [employees],
  );

  const visibleLeaders = leadership.slice(0, 6).map(toChartPerson);
  const focus = leadership[0];
  const focusReports = useMemo(() => {
    if (!focus) return [];
    return employees.filter((e) => e.line_manager_name === focus.full_name);
  }, [employees, focus]);

  if (employees.length === 0) {
    return (
      <Card>
        <div className="empty" style={{ margin: 16 }}>
          <div className="title">No employees yet</div>
          <div className="lede">
            Add people from <strong>People → Add person</strong> and they'll appear here.
          </div>
        </div>
      </Card>
    );
  }

  if (visibleLeaders.length === 0) {
    return (
      <Card>
        <div className="empty" style={{ margin: 16 }}>
          <div className="title">No top-level leaders</div>
          <div className="lede">
            Every employee has a line manager. Promote someone to no-manager status to
            anchor the chart.
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHead
        title="Reporting tree"
        sub="From the top of the company to your team"
      />
      <div
        style={{
          padding: 24,
          overflowX: "auto",
          background: "linear-gradient(180deg, var(--card-2) 0%, var(--card) 100%)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 30 }}>
          <ChartCard
            person={{
              id: "anchor",
              name: visibleLeaders[0].name,
              av: visibleLeaders[0].av,
            }}
            tone="yellow"
            sub={leadership[0]?.job_title_name || "Leadership"}
            badge={`${employees.length} people`}
          />
        </div>

        <svg viewBox="0 0 1200 60" style={{ width: "100%", height: 60, marginBottom: -1 }}>
          <line x1="600" y1="0" x2="600" y2="30" stroke="var(--hairline)" strokeWidth="2" />
          <line x1="120" y1="30" x2="1080" y2="30" stroke="var(--hairline)" strokeWidth="2" />
          {visibleLeaders.map((_, i) => {
            const x = 120 + i * 192;
            return (
              <line
                key={i}
                x1={x}
                y1="30"
                x2={x}
                y2="60"
                stroke="var(--hairline)"
                strokeWidth="2"
              />
            );
          })}
        </svg>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${Math.min(visibleLeaders.length, 6)}, 1fr)`,
            gap: 12,
          }}
        >
          {visibleLeaders.map((leader, idx) => {
            const row = leadership[idx];
            const reportsCount = employees.filter(
              (e) => e.line_manager_name === row?.full_name,
            ).length;
            return (
              <ChartCard
                key={leader.id}
                person={leader}
                sub={row?.department_name || row?.job_title_name}
                badge={reportsCount ? `${reportsCount} reports` : ""}
                onClick={() => navigate(`/people/${leader.id}`)}
              />
            );
          })}
        </div>

        {focusReports.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <svg viewBox="0 0 1200 40" style={{ width: "100%", height: 40 }}>
              <line x1="100" y1="0" x2="100" y2="20" stroke="var(--hairline)" strokeWidth="2" />
              <line
                x1="100"
                y1="20"
                x2="100"
                y2="40"
                stroke="var(--hairline)"
                strokeWidth="2"
                strokeDasharray="3 3"
              />
            </svg>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: `repeat(${Math.min(visibleLeaders.length, 6)}, 1fr)`,
                gap: 12,
              }}
            >
              <div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {focusReports.slice(0, 4).map((p) => (
                    <ChartCard
                      key={p.id}
                      compact
                      person={toChartPerson(p)}
                      sub={p.job_title_name}
                      onClick={() => navigate(`/people/${p.id}`)}
                    />
                  ))}
                  {focusReports.length > 4 && (
                    <div
                      style={{
                        padding: "8px 12px",
                        fontSize: 11.5,
                        color: "var(--action)",
                        fontWeight: 600,
                        background: "var(--info-soft)",
                        border: "1px dashed var(--bunchly)",
                        borderRadius: 8,
                        textAlign: "center",
                        cursor: "pointer",
                      }}
                    >
                      + {focusReports.length - 4} more
                    </div>
                  )}
                </div>
              </div>
              <div
                style={{
                  alignSelf: "start",
                  padding: 12,
                  background: "var(--card-2)",
                  borderRadius: 10,
                  border: "1px dashed var(--hairline)",
                  fontSize: 12,
                  color: "var(--text-3)",
                  textAlign: "center",
                }}
              >
                <I.users
                  size={18}
                  style={{ display: "block", margin: "0 auto 6px", color: "var(--text-4)" }}
                />
                Click a leader to expand
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="card-foot">
        <span style={{ fontSize: 12, color: "var(--text-3)" }}>
          Hold ⌘ + scroll to zoom · drag to pan
        </span>
        <div style={{ display: "flex", gap: 6 }}>
          <Button variant="outline" size="sm">−</Button>
          <Button variant="outline" size="sm">100%</Button>
          <Button variant="outline" size="sm">+</Button>
        </div>
      </div>
    </Card>
  );
}

function DepartmentsGrid({ departments }: { departments: Department[] }) {
  if (departments.length === 0) {
    return (
      <Card>
        <div className="empty" style={{ margin: 16 }}>
          <div className="title">No departments yet</div>
          <div className="lede">
            Use <strong>Add department</strong> above to create your first one.
          </div>
        </div>
      </Card>
    );
  }
  return (
    <div className="grid grid-3">
      {departments.map((d) => (
        <Card key={d.id}>
          <div style={{ padding: 20 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: 12,
              }}
            >
              <div>
                <span className="eyebrow">{(d.code || d.id.slice(0, 6)).toUpperCase()}</span>
                <h3
                  style={{
                    fontSize: 24,
                    color: "var(--ink-3)",
                    margin: "4px 0 0",
                    letterSpacing: "-0.01em",
                  }}
                >
                  {d.name}
                </h3>
              </div>
              <Button variant="ghost" size="icon">
                <I.more size={14} />
              </Button>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 0",
                borderTop: "1px solid var(--hairline-2)",
                borderBottom: "1px solid var(--hairline-2)",
              }}
            >
              {d.head_name ? (
                <>
                  <Avatar name={d.head_name} av={avFor(d.head_name)} size="sm" />
                  <div>
                    <div style={{ fontSize: 12, color: "var(--text-3)" }}>Head of department</div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{d.head_name}</div>
                  </div>
                </>
              ) : (
                <div style={{ fontSize: 12, color: "var(--text-3)" }}>Head not assigned</div>
              )}
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 12,
                marginTop: 14,
                fontSize: 12,
              }}
            >
              <div>
                <div style={{ color: "var(--text-3)" }}>Headcount</div>
                <div style={{ fontSize: 22, color: "var(--ink-3)" }}>{d.employee_count ?? 0}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-3)" }}>Status</div>
                <div style={{ fontSize: 14, color: d.is_active ? "var(--positive)" : "var(--text-3)" }}>
                  {d.is_active ? "Active" : "Inactive"}
                </div>
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

function LocationsView({
  locations,
  employees,
}: {
  locations: { id: string; name: string }[];
  employees: EmployeeListItem[];
}) {
  /* Counts come from the live employee roster. Anything whose work_location
     isn't in the list (e.g. blanks) gets bucketed as "Unassigned". */
  const counts = useMemo(() => {
    const map = new Map<string, number>();
    locations.forEach((l) => map.set(l.name, 0));
    let unassigned = 0;
    for (const e of employees) {
      const name = e.work_location_name;
      if (!name) {
        unassigned++;
        continue;
      }
      map.set(name, (map.get(name) ?? 0) + 1);
    }
    if (unassigned > 0) map.set("Unassigned", unassigned);
    return Array.from(map.entries());
  }, [locations, employees]);

  const total = employees.length || 1;

  if (locations.length === 0 && employees.length === 0) {
    return (
      <Card>
        <div className="empty" style={{ margin: 16 }}>
          <div className="title">No locations yet</div>
          <div className="lede">Locations appear once you add an office or assign work locations to employees.</div>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHead title="People by location" sub="Spread across your offices and remote workforce" />
      <div
        className="card-body"
        style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 32 }}
      >
        <BarChart
          data={counts.map(([l, n]) => ({
            label: l,
            value: n,
            color: l === "Remote" || l === "Unassigned" ? "var(--text-4)" : "var(--action)",
          }))}
          format={(v) => `${v} people`}
        />
        <div>
          {counts.map(([l, n], i) => (
            <div
              key={l}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "10px 0",
                borderBottom: i === counts.length - 1 ? "none" : "1px solid var(--hairline-2)",
              }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <I.pin
                  size={14}
                  style={{ color: l === "Remote" || l === "Unassigned" ? "var(--text-3)" : "var(--action)" }}
                />
                <span style={{ fontWeight: 500 }}>{l}</span>
              </span>
              <span style={{ fontVariantNumeric: "tabular-nums", color: "var(--text-3)" }}>
                {Math.round((n / total) * 100)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

function Directory({ employees }: { employees: EmployeeListItem[] }) {
  const navigate = useNavigate();
  if (employees.length === 0) {
    return (
      <Card>
        <div className="empty" style={{ margin: 16 }}>
          <div className="title">Directory is empty</div>
          <div className="lede">Add your first employee from <strong>People → Add person</strong>.</div>
        </div>
      </Card>
    );
  }
  return (
    <Card>
      <CardHead title="Directory" sub="Browse everyone, search by name, role or department" />
      <div
        style={{
          padding: 16,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: 12,
        }}
      >
        {employees.map((e) => (
          <button
            key={e.id}
            onClick={() => navigate(`/people/${e.id}`)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: 10,
              background: "var(--card)",
              border: "1px solid var(--hairline-2)",
              borderRadius: 10,
              textAlign: "left",
              cursor: "pointer",
            }}
          >
            <Avatar name={e.full_name} av={avFor(e.full_name || e.employee_code)} />
            <div style={{ minWidth: 0 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {e.full_name}
              </div>
              <div
                style={{
                  fontSize: 11.5,
                  color: "var(--text-3)",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {e.job_title_name}
              </div>
            </div>
          </button>
        ))}
      </div>
    </Card>
  );
}

function AddDepartmentModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      createDepartment({
        name: name.trim(),
        code: code.trim() || undefined,
        description: description.trim() || undefined,
        is_active: true,
      }),
    onSuccess: () => {
      toast.push(`Department "${name}" created`, "success");
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setName("");
      setCode("");
      setDescription("");
      onClose();
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string; name?: string[] } } }).response?.data;
      toast.push(detail?.detail || detail?.name?.[0] || "Could not create department", "error");
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
      title="New department"
      sub="Create a department to group your people"
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
            {mutation.isPending ? "Creating…" : "Create department"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="col" style={{ gap: 12 }}>
        <div className="field">
          <label>Name</label>
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Engineering"
            autoFocus
          />
        </div>
        <div className="field">
          <label>Short code (optional)</label>
          <input
            className="input"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="ENG"
            maxLength={16}
          />
        </div>
        <div className="field">
          <label>Description (optional)</label>
          <textarea
            className="textarea"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this department do?"
          />
        </div>
      </form>
    </Modal>
  );
}

export default function OrganisationPage() {
  const { hasPerm } = useAuth();
  const canAddDept = hasPerm("organisation.add_department") || hasPerm("organisation.manage");
  const [tab, setTab] = useState("chart");
  const [showAdd, setShowAdd] = useState(false);

  const employees = useQuery({
    queryKey: ["employees"],
    queryFn: () => listEmployees({ page: 1 }),
  });
  const departments = useQuery({ queryKey: ["departments"], queryFn: listDepartments });
  const locations = useQuery({ queryKey: ["locations"], queryFn: listLocations });

  const employeeRows: EmployeeListItem[] = employees.data?.results ?? [];
  const departmentRows: Department[] = departments.data ?? [];
  const locationRows = locations.data ?? [];

  const isLoading = employees.isLoading || departments.isLoading || locations.isLoading;

  return (
    <div className="page">
      <PageHeader
        eyebrow="The shape of your company"
        title="Organisation"
        lede={
          isLoading
            ? "Loading…"
            : `${employeeRows.length} people · ${departmentRows.length} departments · ${locationRows.length} locations`
        }
        actions={
          <>
            <Button variant="outline" size="sm" leftIcon={<I.download size={14} />}>
              Export chart
            </Button>
            {canAddDept && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.plus size={14} />}
                onClick={() => setShowAdd(true)}
              >
                Add department
              </Button>
            )}
          </>
        }
      />
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "chart", label: "Org chart" },
          { value: "depts", label: "Departments", count: departmentRows.length },
          { value: "locations", label: "Locations", count: locationRows.length },
          { value: "directory", label: "Directory" },
        ]}
      />
      {tab === "chart" && <OrgChart employees={employeeRows} />}
      {tab === "depts" && <DepartmentsGrid departments={departmentRows} />}
      {tab === "locations" && (
        <LocationsView locations={locationRows} employees={employeeRows} />
      )}
      {tab === "directory" && <Directory employees={employeeRows} />}
      <AddDepartmentModal open={showAdd} onClose={() => setShowAdd(false)} />
    </div>
  );
}
