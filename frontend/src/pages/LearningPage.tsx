import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Badge,
  Button,
  Card,
  CardHead,
  KpiCell,
  KpiStrip,
  Meter,
  Modal,
  PageHeader,
  PersonCell,
  Tabs,
  useToast,
} from "@/components/ui";
import { downloadCsv } from "@/lib/export";
import { useAuth } from "@/store/auth";
import { listEmployees } from "@/api/employees";
import {
  createTrainingCourse,
  listTrainingCourses,
  listTrainingRecords,
  markTrainingComplete,
  type TrainingCourse,
  type TrainingRecord,
} from "@/api/hr";

function NewCourseModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [duration, setDuration] = useState("1");
  const [mandatory, setMandatory] = useState(true);

  const create = useMutation({
    mutationFn: createTrainingCourse,
    onSuccess: () => {
      toast.push(`Course '${title}' published`, "success");
      queryClient.invalidateQueries({ queryKey: ["training-courses"] });
      onClose();
      setTitle("");
      setCode("");
      setDescription("");
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not publish course",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || !code.trim()) {
      toast.push("Code and title are required", "error");
      return;
    }
    create.mutate({
      code: code.trim(),
      title: title.trim(),
      description: description.trim(),
      duration_hours: Number(duration) || 1,
      is_mandatory: mandatory,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add course"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={create.isPending}>
            {create.isPending ? "Publishing…" : "Publish"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="grid grid-2" style={{ gap: 14 }}>
          <div className="field">
            <label>Code</label>
            <input
              className="input"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="GDPR-101"
              autoFocus
            />
          </div>
          <div className="field">
            <label>Duration (hours)</label>
            <input
              className="input"
              type="number"
              step="0.5"
              min="0.5"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
            />
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Title</label>
            <input
              className="input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="GDPR essentials"
            />
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Description</label>
            <textarea
              className="textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What learners will know after completing this course."
            />
          </div>
          <label className="checkbox" style={{ gridColumn: "1 / -1" }}>
            <input
              type="checkbox"
              checked={mandatory}
              onChange={(e) => setMandatory(e.target.checked)}
            />
            Mandatory
          </label>
        </div>
      </form>
    </Modal>
  );
}

function CourseCard({
  course,
  records,
  canManage,
}: {
  course: TrainingCourse;
  records: TrainingRecord[];
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const employees = useQuery({
    queryKey: ["employees", "for-learning"],
    queryFn: () => listEmployees(),
    enabled: canManage,
  });
  const [picked, setPicked] = useState("");

  const enrolled = records.filter((r) => r.course === course.id);
  const complete = enrolled.filter((r) => r.status === "complete").length;
  const pct = enrolled.length === 0 ? 0 : Math.round((complete / enrolled.length) * 100);

  const mark = useMutation({
    mutationFn: () => markTrainingComplete({ course: course.id, employee: picked }),
    onSuccess: () => {
      toast.push(`Marked '${course.title}' complete`, "success");
      queryClient.invalidateQueries({ queryKey: ["training-records"] });
      setPicked("");
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not mark complete",
        "error",
      ),
  });

  return (
    <Card>
      <div style={{ padding: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <Badge tone={course.is_mandatory ? "red" : "blue"}>
              {course.is_mandatory ? "Mandatory" : "Optional"}
            </Badge>
            <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-3)", marginLeft: 8 }}>
              {course.code}
            </span>
          </div>
          <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>{course.duration_hours} hr</span>
        </div>
        <h3 style={{ fontSize: 22, color: "var(--ink-3)", margin: "10px 0 4px" }}>{course.title}</h3>
        <div style={{ color: "var(--text-3)", fontSize: 12.5 }}>
          {course.description || (course.validity_period_months ? `Valid ${course.validity_period_months} months` : "No deadline")}
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
          <span>{complete} of {enrolled.length} completed</span>
          <span style={{ fontWeight: 600, color: "var(--ink-3)" }}>{pct}%</span>
        </div>
        <Meter value={complete} max={Math.max(1, enrolled.length)} />
        {canManage && (
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <select
              className="select"
              value={picked}
              onChange={(e) => setPicked(e.target.value)}
              style={{ flex: 1 }}
            >
              <option value="">{employees.isLoading ? "Loading…" : "Pick employee"}</option>
              {(employees.data?.results ?? []).map((e) => (
                <option key={e.id} value={e.id}>
                  {e.full_name || `${e.first_name} ${e.last_name}`}
                </option>
              ))}
            </select>
            <Button
              variant="primary"
              size="sm"
              disabled={!picked || mark.isPending}
              onClick={() => mark.mutate()}
            >
              {mark.isPending ? "…" : "Mark complete"}
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}

export default function LearningPage() {
  const { hasPerm } = useAuth();
  const canManage = hasPerm("learning.manage");
  const [tab, setTab] = useState("courses");
  const [showNew, setShowNew] = useState(false);

  const courses = useQuery({
    queryKey: ["training-courses"],
    queryFn: () => listTrainingCourses(),
  });
  const records = useQuery({
    queryKey: ["training-records"],
    queryFn: () => listTrainingRecords(),
  });

  const courseList = courses.data?.results ?? [];
  const recordList = records.data?.results ?? [];

  const totals = useMemo(() => {
    const totalEnrol = recordList.length;
    const totalComplete = recordList.filter((r) => r.status === "complete").length;
    return {
      pct: totalEnrol === 0 ? 0 : Math.round((totalComplete / totalEnrol) * 100),
      enrol: totalEnrol,
      complete: totalComplete,
    };
  }, [recordList]);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Skills & development"
        title="Learning"
        lede={
          courses.isLoading
            ? "Loading…"
            : `${courseList.length} courses · ${courseList.filter((c) => c.is_mandatory).length} mandatory`
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={() => downloadCsv("courses.csv", courseList)}
            >
              Compliance report
            </Button>
            {canManage && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.plus size={14} />}
                onClick={() => setShowNew(true)}
              >
                Add course
              </Button>
            )}
          </>
        }
      />
      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="Active courses" value={courseList.length} />
        <KpiCell label="Completion rate" value={`${totals.pct}%`} />
        <KpiCell label="Mandatory" value={courseList.filter((c) => c.is_mandatory).length} />
        <KpiCell label="Completions" value={totals.complete} />
      </KpiStrip>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "courses", label: "Courses", count: courseList.length },
          { value: "compliance", label: "Compliance" },
        ]}
      />
      {tab === "courses" && (
        <div className="grid grid-2">
          {courseList.map((c) => (
            <CourseCard key={c.id} course={c} records={recordList} canManage={canManage} />
          ))}
          {courseList.length === 0 && courses.isFetched && (
            <Card>
              <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                No courses yet — publish the first one.
              </div>
            </Card>
          )}
        </div>
      )}
      {tab === "compliance" && (
        <Card>
          <CardHead title="Mandatory training status" sub="Per-employee progress on mandatory courses" />
          <table className="table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Course</th>
                <th>Status</th>
                <th>Completed</th>
                <th>Expires</th>
              </tr>
            </thead>
            <tbody>
              {recordList.map((r) => (
                <tr key={r.id}>
                  <td>
                    <PersonCell name={r.employee_name || "—"} />
                  </td>
                  <td>{r.course_title || "—"}</td>
                  <td>
                    {r.status === "complete" ? (
                      <Badge tone="green" dot>Complete</Badge>
                    ) : r.status === "expired" ? (
                      <Badge tone="red" dot>Expired</Badge>
                    ) : (
                      <Badge tone="yellow" dot>In progress</Badge>
                    )}
                  </td>
                  <td className="muted num">{r.completed_at?.slice(0, 10) || "—"}</td>
                  <td className="muted num">{r.expires_at?.slice(0, 10) || "—"}</td>
                </tr>
              ))}
              {recordList.length === 0 && records.isFetched && (
                <tr>
                  <td colSpan={5}>
                    <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                      No training records yet.
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      )}

      <NewCourseModal open={showNew} onClose={() => setShowNew(false)} />
    </div>
  );
}
