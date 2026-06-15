import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Badge,
  Button,
  Card,
  CardHead,
  Modal,
  PageHeader,
  Pagination,
  PersonCell,
  Stat,
  StatusBadge,
  Tabs,
  useToast,
  usePaginated,
} from "@/components/ui";
import { downloadCsv } from "@/lib/export";
import { useAuth } from "@/store/auth";
import { getMyEmployee, listEmployees } from "@/api/employees";
import {
  clockIn as apiClockIn,
  clockOut as apiClockOut,
  createManualAttendance,
  listAttendanceRecords,
  type AttendanceRecord,
} from "@/api/hr";

function formatHours(ms: number): string {
  const totalMin = Math.max(0, Math.floor(ms / 60000));
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return `${h}h ${String(m).padStart(2, "0")}m`;
}

function formatTime(iso?: string | null) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function ManualEntryModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const employees = useQuery({
    queryKey: ["employees", "for-attendance"],
    queryFn: () => listEmployees(),
    enabled: open,
  });
  const [employee, setEmployee] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [clockInTime, setClockInTime] = useState("08:00");
  const [clockOutTime, setClockOutTime] = useState("17:00");
  const [status, setStatus] = useState("present");

  const create = useMutation({
    mutationFn: () =>
      createManualAttendance({
        employee,
        work_date: date,
        clock_in: new Date(`${date}T${clockInTime}:00`).toISOString(),
        clock_out: new Date(`${date}T${clockOutTime}:00`).toISOString(),
        status,
      }),
    onSuccess: () => {
      toast.push("Entry recorded", "success");
      queryClient.invalidateQueries({ queryKey: ["attendance-records"] });
      onClose();
      setEmployee("");
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not save entry",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!employee) {
      toast.push("Pick an employee", "error");
      return;
    }
    create.mutate();
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Manual entry"
      sub="Use this when an employee forgot to clock or had a special schedule."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={create.isPending}>
            {create.isPending ? "Saving…" : "Save entry"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="field" style={{ marginBottom: 14 }}>
          <label>Employee</label>
          <select className="select" value={employee} onChange={(e) => setEmployee(e.target.value)}>
            <option value="">{employees.isLoading ? "Loading…" : "Pick an employee"}</option>
            {(employees.data?.results ?? []).map((e) => (
              <option key={e.id} value={e.id}>
                {e.full_name || `${e.first_name} ${e.last_name}`}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-2" style={{ marginBottom: 14 }}>
          <div className="field">
            <label>Date</label>
            <input className="input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="field">
            <label>Status</label>
            <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="present">Present</option>
              <option value="remote">Worked remotely</option>
              <option value="absent">Absent</option>
              <option value="on_leave">On leave</option>
              <option value="holiday">Public holiday</option>
            </select>
          </div>
          <div className="field">
            <label>Clock in</label>
            <input
              className="input"
              type="time"
              value={clockInTime}
              onChange={(e) => setClockInTime(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Clock out</label>
            <input
              className="input"
              type="time"
              value={clockOutTime}
              onChange={(e) => setClockOutTime(e.target.value)}
            />
          </div>
        </div>
      </form>
    </Modal>
  );
}

function TodayTable({ records }: { records: AttendanceRecord[] }) {
  const pag = usePaginated(records);
  return (
    <Card>
      <table className="table">
        <thead>
          <tr>
            <th>Person</th>
            <th>Clock in</th>
            <th>Clock out</th>
            <th>Hours</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {pag.slice.map((a) => (
            <tr key={a.id}>
              <td>
                <PersonCell name={a.employee_name || "—"} />
              </td>
              <td className="num">
                {formatTime(a.clock_in) || <span style={{ color: "var(--text-4)" }}>—</span>}
              </td>
              <td className="num">
                {formatTime(a.clock_out) || <span style={{ color: "var(--text-4)" }}>—</span>}
              </td>
              <td className="num" style={{ fontSize: 14 }}>
                {a.worked_minutes ? formatHours(a.worked_minutes * 60_000) : "—"}
              </td>
              <td>
                <StatusBadge status={a.status} />
              </td>
            </tr>
          ))}
          {records.length === 0 && (
            <tr>
              <td colSpan={5}>
                <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                  No attendance recorded yet today.
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

export default function AttendancePage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { hasPerm } = useAuth();
  const canManage = hasPerm("attendance.manage");
  const canClock = hasPerm("attendance.clock");
  const [tab, setTab] = useState("today");
  const [showManual, setShowManual] = useState(false);
  const [tick, setTick] = useState(0);

  const me = useQuery({ queryKey: ["me-employee"], queryFn: getMyEmployee, retry: false });

  const today = new Date().toISOString().slice(0, 10);
  const records = useQuery({
    queryKey: ["attendance-records", today],
    queryFn: () => listAttendanceRecords({ work_date: today }),
  });
  const rows = records.data?.results ?? [];

  const myRecord = useMemo(
    () => (me.data ? rows.find((r) => r.employee === me.data!.id) : undefined),
    [rows, me.data],
  );
  const clocked = !!(myRecord && myRecord.clock_in && !myRecord.clock_out);

  useEffect(() => {
    if (!clocked) return;
    const t = setInterval(() => setTick((n) => n + 1), 30_000);
    return () => clearInterval(t);
  }, [clocked]);

  const sessionMs = useMemo(() => {
    void tick;
    if (!clocked || !myRecord?.clock_in) return 0;
    return Date.now() - new Date(myRecord.clock_in).getTime();
  }, [clocked, myRecord?.clock_in, tick]);

  const clockInMut = useMutation({
    mutationFn: () => apiClockIn(),
    onSuccess: () => {
      toast.push("Clocked in", "success");
      queryClient.invalidateQueries({ queryKey: ["attendance-records"] });
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not clock in",
        "error",
      ),
  });
  const clockOutMut = useMutation({
    mutationFn: () => apiClockOut(),
    onSuccess: () => {
      toast.push("Clocked out", "success");
      queryClient.invalidateQueries({ queryKey: ["attendance-records"] });
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not clock out",
        "error",
      ),
  });

  function toggleClock() {
    if (!me.data) {
      toast.push("No employee profile found for your user", "error");
      return;
    }
    if (clocked) clockOutMut.mutate();
    else clockInMut.mutate();
  }

  const exceptions = rows.filter(
    (a) => a.status === "absent" || a.status === "on_leave" || !a.clock_in,
  );

  return (
    <div className="page">
      <PageHeader
        eyebrow="Time tracking"
        title="Attendance"
        lede={records.isLoading ? "Loading…" : "Today's working day."}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={() => downloadCsv("attendance.csv", rows)}
            >
              Export
            </Button>
            {canManage && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.plus size={14} />}
                onClick={() => setShowManual(true)}
              >
                Manual entry
              </Button>
            )}
          </>
        }
      />

      <div
        className="grid"
        style={{ gridTemplateColumns: "1.4fr 1fr 1fr 1fr", gap: 16, marginBottom: 20 }}
      >
        <Card tone="ink">
          <div style={{ padding: 22, display: "flex", alignItems: "center", gap: 20 }}>
            <div>
              <span className="eyebrow" style={{ color: "var(--yellow)" }}>
                {clocked ? "Working" : "Clocked out"}
              </span>
              <div style={{ fontSize: 36, color: "#fff", marginTop: 6 }}>
                {clocked
                  ? formatHours(sessionMs)
                  : myRecord?.worked_minutes
                    ? formatHours(myRecord.worked_minutes * 60_000)
                    : "0h 00m"}
              </div>
              <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", marginTop: 2 }}>
                {clocked
                  ? `Started ${formatTime(myRecord!.clock_in)} · ${me.data?.full_name || me.data?.first_name || "you"}`
                  : me.data
                    ? "Tap to clock in"
                    : "No employee profile for your user"}
              </div>
            </div>
            <div style={{ marginLeft: "auto" }}>
              <Button
                variant="yellow"
                size="lg"
                leftIcon={<I.clock size={16} />}
                disabled={!me.data || clockInMut.isPending || clockOutMut.isPending}
                title={
                  !me.data
                    ? "No employee profile linked to your user — ask HR to link one."
                    : clocked
                      ? "Clock out"
                      : "Clock in"
                }
                onClick={toggleClock}
              >
                {clocked ? "Clock out" : "Clock in"}
              </Button>
            </div>
          </div>
        </Card>
        <Card>
          <div style={{ padding: 18 }}>
            <Stat
              label="Working today"
              value={rows.filter((a) => a.status === "present" || a.status === "remote").length}
              sub={`of ${rows.length}`}
            />
          </div>
        </Card>
        <Card>
          <div style={{ padding: 18 }}>
            <Stat
              label="On leave today"
              value={rows.filter((a) => a.status === "on_leave").length}
              sub=""
            />
          </div>
        </Card>
        <Card>
          <div style={{ padding: 18 }}>
            <Stat
              label="Hours today"
              value={`${(rows.reduce((a, r) => a + Number(r.worked_minutes || 0), 0) / 60).toFixed(1)}h`}
              sub={`${rows.length} entries`}
            />
          </div>
        </Card>
      </div>

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "today", label: "Today", count: rows.length },
          { value: "exceptions", label: "Exceptions", count: exceptions.length },
        ]}
      />
      {tab === "today" && <TodayTable records={rows} />}
      {tab === "exceptions" && (
        <Card>
          <CardHead title="Exceptions" sub="Absences, leave, missing clock-ins" />
          <table className="table">
            <thead>
              <tr>
                <th>Person</th>
                <th>Exception</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {exceptions.map((a) => (
                <tr key={a.id}>
                  <td>
                    <PersonCell name={a.employee_name || "—"} />
                  </td>
                  <td>
                    <Badge tone="yellow" dot>
                      {a.status}
                    </Badge>
                  </td>
                  <td className="muted">{a.clock_in ? `In at ${formatTime(a.clock_in)}` : "Never clocked in"}</td>
                </tr>
              ))}
              {exceptions.length === 0 && (
                <tr>
                  <td colSpan={3}>
                    <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                      No exceptions today.
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      )}

      <ManualEntryModal open={showManual} onClose={() => setShowManual(false)} />
    </div>
  );
}
