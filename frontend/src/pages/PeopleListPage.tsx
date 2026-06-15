import { useMemo, useState, type CSSProperties, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Avatar,
  Badge,
  Button,
  Card,
  KpiCell,
  KpiStrip,
  Modal,
  PageHeader,
  Pagination,
  StatusBadge,
  useToast,
  usePaginated,
} from "@/components/ui";
import { downloadCsv } from "@/lib/export";
import { fmtDate } from "@/lib/format";
import { useAuth } from "@/store/auth";
import {
  createEmployee,
  listEmployees,
  type EmployeeListItem,
} from "@/api/employees";
import { listDepartments, listJobTitles } from "@/api/organisation";

function iconToggle(active: boolean): CSSProperties {
  return {
    width: 28,
    height: 28,
    borderRadius: 6,
    background: active ? "var(--card)" : "transparent",
    boxShadow: active ? "0 1px 3px rgba(20,30,44,0.1)" : "none",
    color: active ? "var(--ink)" : "var(--text-3)",
    display: "grid",
    placeItems: "center",
    border: "none",
    cursor: "pointer",
  };
}

function AddPersonModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const departments = useQuery({
    queryKey: ["departments"],
    queryFn: listDepartments,
    enabled: open,
  });
  const jobTitles = useQuery({
    queryKey: ["job-titles"],
    queryFn: listJobTitles,
    enabled: open,
  });
  const colleagues = useQuery({
    queryKey: ["employees", "for-manager"],
    queryFn: () => listEmployees(),
    enabled: open,
  });

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [employeeNumber, setEmployeeNumber] = useState("");
  const [email, setEmail] = useState("");
  const [department, setDepartment] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [manager, setManager] = useState("");
  const [employmentType, setEmploymentType] = useState("full_time");
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));

  const create = useMutation({
    mutationFn: createEmployee,
    onSuccess: (rec) => {
      toast.push(`Employee ${rec.employee_code || rec.id.slice(0, 6)} created`, "success");
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      onClose();
      setFirstName("");
      setLastName("");
      setEmployeeNumber("");
      setEmail("");
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not create employee",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!firstName.trim() || !lastName.trim() || !employeeNumber.trim()) {
      toast.push("First name, last name and employee number are required", "error");
      return;
    }
    create.mutate({
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      employee_number: employeeNumber.trim(),
      work_email: email.trim() || undefined,
      department: department || undefined,
      job_title: jobTitle || undefined,
      line_manager: manager || undefined,
      employment_type: employmentType,
      start_date: startDate,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add a new person"
      sub="They'll show up in the directory immediately."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={create.isPending}>
            {create.isPending ? "Creating…" : "Create"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="grid grid-2" style={{ gap: 14 }}>
          <div className="field">
            <label>First name</label>
            <input className="input" value={firstName} onChange={(e) => setFirstName(e.target.value)} autoFocus />
          </div>
          <div className="field">
            <label>Last name</label>
            <input className="input" value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </div>
          <div className="field">
            <label>Employee number</label>
            <input
              className="input"
              value={employeeNumber}
              onChange={(e) => setEmployeeNumber(e.target.value)}
              placeholder="E-0123"
            />
          </div>
          <div className="field">
            <label>Work email</label>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label>Department</label>
            <select className="select" value={department} onChange={(e) => setDepartment(e.target.value)}>
              <option value="">{departments.isLoading ? "Loading…" : "No department"}</option>
              {(departments.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Job title</label>
            <select className="select" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)}>
              <option value="">{jobTitles.isLoading ? "Loading…" : "No job title"}</option>
              {(jobTitles.data ?? []).map((j) => (
                <option key={j.id} value={j.id}>
                  {j.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Line manager</label>
            <select className="select" value={manager} onChange={(e) => setManager(e.target.value)}>
              <option value="">No manager</option>
              {(colleagues.data?.results ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.full_name || `${c.first_name} ${c.last_name}`}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Employment type</label>
            <select className="select" value={employmentType} onChange={(e) => setEmploymentType(e.target.value)}>
              <option value="full_time">Full time</option>
              <option value="part_time">Part time</option>
              <option value="contract">Contract</option>
              <option value="temporary">Temporary</option>
              <option value="intern">Intern</option>
              <option value="consultant">Consultant</option>
            </select>
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
        </div>
      </form>
    </Modal>
  );
}

function statusTone(status: string): string {
  if (status === "active") return "Active";
  if (status === "on_leave") return "On Leave";
  if (status === "probation") return "Probation";
  if (status === "terminated") return "Terminated";
  if (status === "resigned") return "Resigned";
  return status;
}

export default function PeopleListPage() {
  const navigate = useNavigate();
  const { effectiveRole, hasPerm } = useAuth();
  const canAdd = hasPerm("employees.add_employee");
  const [view, setView] = useState<"table" | "grid">("table");
  const [search, setSearch] = useState("");
  const [dept, setDept] = useState("All");
  const [showAdd, setShowAdd] = useState(false);

  const employees = useQuery({
    queryKey: ["employees"],
    queryFn: () => listEmployees(),
  });
  const departments = useQuery({ queryKey: ["departments"], queryFn: listDepartments });

  const rows: EmployeeListItem[] = employees.data?.results ?? [];

  const filtered = useMemo(() => {
    let r = rows;
    if (search) {
      const s = search.toLowerCase();
      r = r.filter((e) =>
        ((e.full_name || "") + (e.job_title_name || "") + e.employee_code)
          .toLowerCase()
          .includes(s),
      );
    }
    if (dept !== "All") r = r.filter((e) => e.department_name === dept);
    return r;
  }, [search, dept, rows]);

  const pag = usePaginated(filtered);

  const probationCount = rows.filter((e) => e.employment_status === "probation").length;
  const onLeaveCount = rows.filter((e) => e.employment_status === "on_leave").length;
  const activeCount = rows.filter((e) => e.employment_status === "active").length;
  const contractCount = rows.filter((e) => e.employment_type === "contract").length;

  return (
    <div className="page">
      <PageHeader
        eyebrow={effectiveRole === "manager" ? "Direct reports" : "Workforce"}
        title="People"
        lede={
          employees.isLoading
            ? "Loading…"
            : `${rows.length} employees · ${(departments.data ?? []).length} departments`
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={() => downloadCsv("employees.csv", filtered)}
            >
              Export
            </Button>
            {canAdd && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.plus size={14} />}
                onClick={() => setShowAdd(true)}
              >
                Add person
              </Button>
            )}
          </>
        }
      />
      {effectiveRole === "hr" && (
        <KpiStrip cols={4} style={{ marginBottom: 20 }}>
          <KpiCell label="Active" value={activeCount} />
          <KpiCell label="On leave" value={onLeaveCount} />
          <KpiCell label="Probation" value={probationCount} />
          <KpiCell label="Contractors" value={contractCount} />
        </KpiStrip>
      )}
      <Card padded>
        <div className="table-toolbar">
          <div className="toolbar-search">
            <span className="icon">
              <I.search size={16} />
            </span>
            <input
              placeholder="Search by name, title or code…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            className="select"
            style={{ width: 200, height: 34 }}
            value={dept}
            onChange={(e) => setDept(e.target.value)}
          >
            <option>All</option>
            {(departments.data ?? []).map((d) => (
              <option key={d.id}>{d.name}</option>
            ))}
          </select>
          <div
            style={{
              marginLeft: "auto",
              display: "flex",
              gap: 4,
              padding: 3,
              background: "var(--mist)",
              borderRadius: 8,
            }}
          >
            <button onClick={() => setView("table")} style={iconToggle(view === "table")}>
              <I.list size={14} />
            </button>
            <button onClick={() => setView("grid")} style={iconToggle(view === "grid")}>
              <I.grid size={14} />
            </button>
          </div>
        </div>
        {view === "table" ? (
          <table className="table">
            <thead>
              <tr>
                <th>Person</th>
                <th>Department</th>
                <th>Location</th>
                <th>Type</th>
                <th>Joined</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {pag.slice.map((e) => (
                <tr key={e.id} className="clickable" onClick={() => navigate(`/people/${e.id}`)}>
                  <td>
                    <div className="cell-person">
                      <Avatar name={e.full_name || `${e.first_name} ${e.last_name}`} />
                      <div className="meta">
                        <div className="name">
                          {e.full_name || `${e.first_name} ${e.last_name}`}{" "}
                          {e.employment_status === "probation" && (
                            <Badge tone="yellow" className="num" style={{ marginLeft: 6, fontSize: 10 }}>
                              Probation
                            </Badge>
                          )}
                        </div>
                        <div className="sub">
                          {e.job_title_name || "—"} · {e.employee_code}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td>{e.department_name || "—"}</td>
                  <td>{e.work_location_name || "—"}</td>
                  <td style={{ color: "var(--text-2)" }}>{e.employment_type || "—"}</td>
                  <td className="muted">{e.start_date ? fmtDate(e.start_date) : "—"}</td>
                  <td>
                    <StatusBadge status={statusTone(e.employment_status)} />
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <I.chevron size={14} style={{ color: "var(--text-3)" }} />
                  </td>
                </tr>
              ))}
              {rows.length === 0 && employees.isFetched && (
                <tr>
                  <td colSpan={7}>
                    <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                      No employees yet.
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        ) : (
          <div className="grid grid-3" style={{ padding: 16 }}>
            {pag.slice.map((e) => (
              <div
                key={e.id}
                onClick={() => navigate(`/people/${e.id}`)}
                style={{
                  background: "var(--card)",
                  border: "1px solid var(--hairline)",
                  borderRadius: 14,
                  padding: 16,
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", gap: 12 }}>
                  <Avatar name={e.full_name || `${e.first_name} ${e.last_name}`} size="lg" />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>
                      {e.full_name || `${e.first_name} ${e.last_name}`}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-3)" }}>{e.job_title_name || "—"}</div>
                    <div style={{ fontSize: 11, color: "var(--text-4)", marginTop: 4 }}>{e.employee_code}</div>
                  </div>
                </div>
                <div className="divider" />
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 12,
                    color: "var(--text-3)",
                  }}
                >
                  <span>{e.department_name || "—"}</span>
                  <StatusBadge status={statusTone(e.employment_status)} />
                </div>
              </div>
            ))}
          </div>
        )}
        <Pagination
          page={pag.page}
          pages={pag.pages}
          pageSize={pag.pageSize}
          total={pag.total}
          setPage={pag.setPage}
        />
      </Card>

      <AddPersonModal open={showAdd} onClose={() => setShowAdd(false)} />
    </div>
  );
}
