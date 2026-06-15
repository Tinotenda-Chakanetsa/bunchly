import { useMemo, useState, type FormEvent } from "react";
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
  useToast,
} from "@/components/ui";
import { downloadCsv } from "@/lib/export";
import { listEmployees } from "@/api/employees";
import { useAuth } from "@/store/auth";
import {
  addOnboardingTask,
  getProgramme,
  listChecklistTemplates,
  listProgrammes,
  setTaskStatus,
  startProgramme,
} from "@/api/onboarding";

const OWNER_ROLES = [
  { value: "hr", label: "HR" },
  { value: "manager", label: "Manager" },
  { value: "it", label: "IT" },
  { value: "finance", label: "Finance" },
  { value: "employee", label: "Employee" },
];

function StartProgrammeModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const employees = useQuery({
    queryKey: ["employees", "lookup"],
    queryFn: () => listEmployees({ search: "" }),
    enabled: open,
  });
  const templates = useQuery({
    queryKey: ["checklist-templates"],
    queryFn: listChecklistTemplates,
    enabled: open,
  });
  const [employee, setEmployee] = useState("");
  const [programmeType, setProgrammeType] = useState("onboarding");
  const [template, setTemplate] = useState("");
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));

  const create = useMutation({
    mutationFn: startProgramme,
    onSuccess: () => {
      toast.push("Programme started", "success");
      queryClient.invalidateQueries({ queryKey: ["onboarding-programmes"] });
      onClose();
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not start programme",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!employee) {
      toast.push("Pick an employee", "error");
      return;
    }
    create.mutate({
      employee,
      programme_type: programmeType,
      template: template || undefined,
      start_date: startDate,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Start programme"
      sub="Pre-fills tasks from the chosen template."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={create.isPending}>
            Cancel
          </Button>
          <Button variant="primary" onClick={submit} disabled={create.isPending}>
            {create.isPending ? "Starting…" : "Start programme"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="grid grid-2" style={{ gap: 12 }}>
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
            <label>Type</label>
            <select
              className="select"
              value={programmeType}
              onChange={(e) => setProgrammeType(e.target.value)}
            >
              <option value="onboarding">Onboarding</option>
              <option value="offboarding">Offboarding</option>
            </select>
          </div>
          <div className="field">
            <label>Template (optional)</label>
            <select
              className="select"
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
            >
              <option value="">No template</option>
              {(templates.data ?? [])
                .filter((t) => t.programme_type === programmeType)
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}{t.is_default ? " (default)" : ""}
                  </option>
                ))}
            </select>
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
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

export default function OnboardingPage() {
  const navigate = useNavigate();
  const { hasPerm } = useAuth();
  const canManage = hasPerm("onboarding.manage");
  const [showStart, setShowStart] = useState(false);

  const programmes = useQuery({
    queryKey: ["onboarding-programmes"],
    queryFn: () => listProgrammes({ programme_type: "onboarding" }),
  });

  const rows = programmes.data?.results ?? [];
  const counts = useMemo(() => {
    const stats = { total: 0, completed: 0, avgProgress: 0 };
    rows.forEach((p) => {
      stats.total += 1;
      const done = p.tasks?.filter((t) => t.status === "complete").length || 0;
      const total = p.tasks?.length || 0;
      const progress = total === 0 ? 0 : Math.round((done / total) * 100);
      if (progress >= 100) stats.completed += 1;
      stats.avgProgress += progress;
    });
    if (rows.length > 0) stats.avgProgress = Math.round(stats.avgProgress / rows.length);
    return stats;
  }, [rows]);

  return (
    <div className="page">
      <PageHeader
        eyebrow="People in motion"
        title="Onboarding"
        lede={programmes.isLoading ? "Loading…" : `${counts.total} programmes in flight`}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={() =>
                downloadCsv(
                  `onboarding-programmes-${new Date().toISOString().slice(0, 10)}.csv`,
                  rows.map((p) => ({
                    id: p.id,
                    employee: p.employee_name,
                    type: p.programme_type,
                    template: p.template_name,
                    status: p.status,
                    start_date: p.start_date,
                    tasks: p.tasks?.length || 0,
                  })),
                )
              }
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
                Start programme
              </Button>
            )}
          </>
        }
      />

      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="Active programmes" value={counts.total} sub="In flight now" />
        <KpiCell label="Avg completion" value={`${counts.avgProgress}%`} deltaTone="up" />
        <KpiCell label="Fully wrapped" value={counts.completed} sub="At 100% complete" />
        <KpiCell label="Templates" value="—" sub="Configured per type" />
      </KpiStrip>

      <div className="grid grid-2">
        {rows.map((p) => {
          const done = p.tasks?.filter((t) => t.status === "complete").length || 0;
          const total = p.tasks?.length || 0;
          const progress = total === 0 ? 0 : Math.round((done / total) * 100);
          return (
            <Card
              key={p.id}
              onClick={() => navigate(`/onboarding/${p.id}`)}
              style={{ cursor: "pointer" }}
            >
              <div style={{ padding: 20 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: 12,
                  }}
                >
                  <span className="eyebrow">{p.id.slice(0, 8)}</span>
                  <Badge tone={progress >= 80 ? "green" : progress >= 40 ? "blue" : "yellow"} dot>
                    {progress >= 80 ? "Wrapping up" : progress >= 40 ? "In progress" : "Just started"}
                  </Badge>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <Avatar name={p.employee_name || "?"} size="lg" />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 22, color: "var(--ink-3)", letterSpacing: "-0.01em" }}>
                      {p.employee_name}
                    </div>
                    <div style={{ color: "var(--text-3)", fontSize: 12.5 }}>
                      {p.template_name || "Custom programme"}
                    </div>
                    <div style={{ color: "var(--text-4)", fontSize: 12, marginTop: 2 }}>
                      {p.status_display || p.status}
                    </div>
                  </div>
                </div>
                <div className="divider" />
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 12,
                    color: "var(--text-3)",
                    marginBottom: 6,
                  }}
                >
                  <span>
                    {done} of {total} tasks complete
                  </span>
                  <span style={{ fontWeight: 600, color: "var(--ink-3)" }}>{progress}%</span>
                </div>
                <Meter value={progress} />
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 11.5,
                    color: "var(--text-3)",
                    marginTop: 12,
                  }}
                >
                  <span>Started {p.start_date}</span>
                  {p.target_completion_date && <span>Target {p.target_completion_date}</span>}
                </div>
              </div>
            </Card>
          );
        })}
        {programmes.isFetched && rows.length === 0 && (
          <Card>
            <div className="empty">
              <div className="title">No onboarding programmes yet</div>
              <div className="lede">Click <strong>Start programme</strong> to add the first one.</div>
            </div>
          </Card>
        )}
      </div>

      <StartProgrammeModal open={showStart} onClose={() => setShowStart(false)} />
    </div>
  );
}

function AddTaskModal({
  open,
  onClose,
  programmeId,
}: {
  open: boolean;
  onClose: () => void;
  programmeId: string;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [ownerRole, setOwnerRole] = useState("hr");
  const [dueDate, setDueDate] = useState("");

  const add = useMutation({
    mutationFn: addOnboardingTask,
    onSuccess: () => {
      toast.push("Task added", "success");
      queryClient.invalidateQueries({ queryKey: ["programme", programmeId] });
      onClose();
      setTitle("");
      setDescription("");
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    add.mutate({
      programme: programmeId,
      title: title.trim(),
      description,
      owner_role: ownerRole,
      due_date: dueDate || null,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add task"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={add.isPending}>
            {add.isPending ? "Adding…" : "Add task"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="grid grid-2" style={{ gap: 12 }}>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Title</label>
            <input
              className="input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Provision Slack & email"
              autoFocus
            />
          </div>
          <div className="field">
            <label>Owner role</label>
            <select
              className="select"
              value={ownerRole}
              onChange={(e) => setOwnerRole(e.target.value)}
            >
              {OWNER_ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Due date (optional)</label>
            <input
              className="input"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Description (optional)</label>
            <textarea
              className="textarea"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>
      </form>
    </Modal>
  );
}

export function ProgrammeDetailPage() {
  const navigate = useNavigate();
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { hasPerm } = useAuth();
  const canManage = hasPerm("onboarding.manage");
  const [showAdd, setShowAdd] = useState(false);

  const programme = useQuery({
    queryKey: ["programme", id],
    queryFn: () => getProgramme(id),
    enabled: Boolean(id),
  });

  const toggle = useMutation({
    mutationFn: (vars: { id: string; status: "pending" | "complete" }) =>
      setTaskStatus(vars.id, vars.status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["programme", id] });
    },
    onError: () => toast.push("Could not update task", "error"),
  });

  if (programme.isLoading) {
    return (
      <div className="page">
        <div style={{ padding: 40, color: "var(--text-3)" }}>Loading…</div>
      </div>
    );
  }
  if (programme.isError || !programme.data) {
    return (
      <div className="page">
        <Button variant="ghost" size="sm" onClick={() => navigate("/onboarding")}>← Back</Button>
        <div className="empty">
          <div className="title">Programme not found</div>
        </div>
      </div>
    );
  }

  const p = programme.data;
  const tasks = p.tasks || [];
  const done = tasks.filter((t) => t.status === "complete").length;
  const total = tasks.length;
  const progress = total === 0 ? 0 : Math.round((done / total) * 100);

  return (
    <div className="page">
      <Button
        variant="ghost"
        size="sm"
        style={{ marginBottom: 16 }}
        onClick={() => navigate("/onboarding")}
      >
        <I.chevron size={14} style={{ transform: "rotate(180deg)" }} /> Back to Onboarding
      </Button>

      <Card>
        <div style={{ padding: 28, display: "flex", gap: 22, alignItems: "center" }}>
          <Avatar name={p.employee_name || "?"} size="xl" />
          <div style={{ flex: 1 }}>
            <span className="eyebrow">{p.programme_type_display || p.programme_type} · {p.id.slice(0, 8)}</span>
            <h1 style={{ fontSize: 32, color: "var(--ink-3)", margin: "6px 0 4px" }}>
              {p.employee_name}
            </h1>
            <div style={{ color: "var(--text-2)" }}>
              {p.template_name || "Custom"} · started {p.start_date}
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 42, color: "var(--ink-3)", lineHeight: 1 }}>{progress}%</div>
            <div style={{ fontSize: 12, color: "var(--text-3)" }}>
              {done} of {total} tasks
            </div>
          </div>
        </div>
      </Card>

      <div className="grid" style={{ gridTemplateColumns: "2fr 1fr", gap: 20, marginTop: 20 }}>
        <Card>
          <CardHead
            title="Checklist"
            sub="Tap a task to mark it complete"
            action={
              canManage ? (
                <Button
                  variant="primary"
                  size="sm"
                  leftIcon={<I.plus size={14} />}
                  onClick={() => setShowAdd(true)}
                >
                  Add task
                </Button>
              ) : null
            }
          />
          <div className="card-body">
            {tasks.length === 0 && (
              <div className="empty">
                <div className="title">No tasks yet</div>
                <div className="lede">Add the first task above.</div>
              </div>
            )}
            {tasks.map((t, i) => {
              const checked = t.status === "complete";
              return (
                <div
                  key={t.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "10px 0",
                    borderBottom: i === tasks.length - 1 ? "none" : "1px solid var(--hairline-2)",
                  }}
                >
                  <button
                    onClick={() =>
                      toggle.mutate({ id: t.id, status: checked ? "pending" : "complete" })
                    }
                    disabled={toggle.isPending}
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: 6,
                      border: checked ? "2px solid var(--positive)" : "2px solid var(--hairline)",
                      background: checked ? "var(--positive)" : "var(--card)",
                      color: "#fff",
                      display: "grid",
                      placeItems: "center",
                      flexShrink: 0,
                      cursor: "pointer",
                    }}
                  >
                    {checked && <I.check size={11} strokeWidth={3} />}
                  </button>
                  <div
                    style={{
                      flex: 1,
                      fontSize: 13.5,
                      fontWeight: 500,
                      color: checked ? "var(--text-3)" : "var(--text)",
                      textDecoration: checked ? "line-through" : "none",
                      cursor: "pointer",
                    }}
                    onClick={() =>
                      toggle.mutate({ id: t.id, status: checked ? "pending" : "complete" })
                    }
                  >
                    {t.title}
                  </div>
                  <Badge tone="outline">{t.owner_role_display || t.owner_role}</Badge>
                </div>
              );
            })}
          </div>
        </Card>

        <Card>
          <CardHead title="Programme" />
          <div className="card-body" style={{ paddingTop: 4, fontSize: 13 }}>
            <div style={{ padding: "8px 0", borderBottom: "1px solid var(--hairline-2)", display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-3)" }}>Status</span>
              <span>{p.status_display || p.status}</span>
            </div>
            <div style={{ padding: "8px 0", borderBottom: "1px solid var(--hairline-2)", display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-3)" }}>Started</span>
              <span>{p.start_date}</span>
            </div>
            {p.target_completion_date && (
              <div style={{ padding: "8px 0", borderBottom: "1px solid var(--hairline-2)", display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-3)" }}>Target</span>
                <span>{p.target_completion_date}</span>
              </div>
            )}
            {p.completed_at && (
              <div style={{ padding: "8px 0", display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-3)" }}>Completed</span>
                <span>{p.completed_at}</span>
              </div>
            )}
          </div>
        </Card>
      </div>

      <AddTaskModal open={showAdd} onClose={() => setShowAdd(false)} programmeId={p.id} />
    </div>
  );
}
