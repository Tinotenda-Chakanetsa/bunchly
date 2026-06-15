/* HR Cases — backend-driven. Used by AdminPages.tsx via re-export so
   the rest of the admin file (Imports, Policies, Reports, Settings,
   Audit Logs) can be migrated incrementally. */
import { useMemo, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listCaseCategories } from "@/api/hr";

import { I } from "@/components/icons";
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardHead,
  KpiCell,
  KpiStrip,
  Modal,
  PageHeader,
  Pagination,
  PersonCell,
  StatusBadge,
  Tabs,
  useToast,
  usePaginated,
} from "@/components/ui";
import { downloadCsv } from "@/lib/export";
import {
  addCaseComment,
  assignCase,
  changeCaseStatus,
  getHRCase,
  listCaseComments,
  listHRCases,
  raiseHRCase,
  resolveCase,
} from "@/api/hr";
import { useAuth } from "@/store/auth";

const PRIORITIES: Array<"low" | "medium" | "high" | "urgent"> = [
  "low",
  "medium",
  "high",
  "urgent",
];

function NewCaseModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const categories = useQuery({
    queryKey: ["case-categories"],
    queryFn: listCaseCategories,
    enabled: open,
  });
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState<"low" | "medium" | "high" | "urgent">("medium");
  const [description, setDescription] = useState("");

  const raise = useMutation({
    mutationFn: raiseHRCase,
    onSuccess: (rec) => {
      toast.push(`Case ${rec.case_number || rec.id.slice(0, 8)} raised`, "success");
      queryClient.invalidateQueries({ queryKey: ["hr-cases"] });
      onClose();
      setSubject("");
      setDescription("");
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not raise case",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!subject.trim() || !description.trim()) return;
    raise.mutate({
      category: category || undefined,
      subject: subject.trim(),
      description: description.trim(),
      priority,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Raise an HR case"
      sub="HR is notified instantly."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={raise.isPending}>
            {raise.isPending ? "Submitting…" : "Submit"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="field" style={{ marginBottom: 12 }}>
          <label>Subject</label>
          <input
            className="input"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Short summary"
            autoFocus
          />
        </div>
        <div className="grid grid-2" style={{ marginBottom: 12 }}>
          <div className="field">
            <label>Category</label>
            <select className="select" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">{categories.isLoading ? "Loading…" : "No category"}</option>
              {(categories.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Priority</label>
            <select
              className="select"
              value={priority}
              onChange={(e) =>
                setPriority(e.target.value as "low" | "medium" | "high" | "urgent")
              }
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="field">
          <label>What's going on?</label>
          <textarea
            className="textarea"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Walk us through it..."
          />
        </div>
      </form>
    </Modal>
  );
}

export function HRCasesPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("all");
  const [showNew, setShowNew] = useState(false);

  const cases = useQuery({ queryKey: ["hr-cases"], queryFn: () => listHRCases() });
  const rows = cases.data?.results ?? [];

  const filtered = useMemo(() => {
    if (tab === "open") return rows.filter((c) => c.status === "open");
    if (tab === "mine") return rows.filter((c) => c.assignee);
    return rows;
  }, [tab, rows]);

  const pag = usePaginated(filtered);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Employee support"
        title="HR cases"
        lede={
          cases.isLoading
            ? "Loading…"
            : `${rows.filter((c) => c.status === "open").length} open`
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={() => downloadCsv("hr-cases.csv", rows)}
            >
              Export
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<I.plus size={14} />}
              onClick={() => setShowNew(true)}
            >
              Raise a case
            </Button>
          </>
        }
      />
      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="Open" value={rows.filter((c) => c.status === "open").length} />
        <KpiCell label="In progress" value={rows.filter((c) => c.status === "in_progress").length} />
        <KpiCell label="Resolved" value={rows.filter((c) => c.status === "resolved").length} />
        <KpiCell label="Awaiting employee" value={rows.filter((c) => c.status === "awaiting_employee").length} />
      </KpiStrip>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "all", label: "All", count: rows.length },
          { value: "open", label: "Open", count: rows.filter((c) => c.status === "open").length },
          { value: "mine", label: "Assigned" },
        ]}
      />
      <Card>
        <table className="table">
          <thead>
            <tr>
              <th>Case</th>
              <th>Raised by</th>
              <th>Category</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Assignee</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {pag.slice.map((c) => (
              <tr key={c.id} className="clickable" onClick={() => navigate(`/hr-cases/${c.id}`)}>
                <td>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{c.subject}</div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-3)" }}>
                    {c.case_number || c.id.slice(0, 8)}
                  </div>
                </td>
                <td>
                  <PersonCell name={c.raised_by_name || "—"} />
                </td>
                <td>
                  <Badge tone="outline">{c.category_name || c.category}</Badge>
                </td>
                <td>
                  <Badge tone={c.priority === "high" ? "red" : c.priority === "low" ? "soft" : "blue"} dot>
                    {c.priority}
                  </Badge>
                </td>
                <td>
                  <StatusBadge status={c.status_display || c.status} />
                </td>
                <td className="muted">{c.assignee_name || "—"}</td>
                <td className="muted">{c.updated_at?.slice(0, 10) || "—"}</td>
              </tr>
            ))}
            {rows.length === 0 && cases.isFetched && (
              <tr>
                <td colSpan={7}>
                  <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                    No cases yet.
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
      <NewCaseModal open={showNew} onClose={() => setShowNew(false)} />
    </div>
  );
}

export function CaseDetailPage() {
  const navigate = useNavigate();
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const toast = useToast();
  const [draft, setDraft] = useState("");
  const [internal, setInternal] = useState(false);

  const caseQ = useQuery({
    queryKey: ["hr-case", id],
    queryFn: () => getHRCase(id),
    enabled: Boolean(id),
  });
  const commentsQ = useQuery({
    queryKey: ["case-comments", id],
    queryFn: () => listCaseComments(id),
    enabled: Boolean(id),
  });

  const reply = useMutation({
    mutationFn: () =>
      addCaseComment({ case: id, body: draft.trim(), is_internal: internal }),
    onSuccess: () => {
      toast.push(internal ? "Internal note added" : "Reply sent", "success");
      queryClient.invalidateQueries({ queryKey: ["case-comments", id] });
      queryClient.invalidateQueries({ queryKey: ["hr-case", id] });
      setDraft("");
      setInternal(false);
    },
  });

  const setStatus = useMutation({
    mutationFn: (status: string) => changeCaseStatus(id, status),
    onSuccess: () => {
      toast.push("Status updated", "success");
      queryClient.invalidateQueries({ queryKey: ["hr-case", id] });
      queryClient.invalidateQueries({ queryKey: ["hr-cases"] });
    },
  });

  const takeOwnership = useMutation({
    mutationFn: () => assignCase(id, user?.id || ""),
    onSuccess: () => {
      toast.push("Taken ownership", "success");
      queryClient.invalidateQueries({ queryKey: ["hr-case", id] });
    },
  });

  const resolveMut = useMutation({
    mutationFn: () => resolveCase(id, "Resolved by HR"),
    onSuccess: () => {
      toast.push("Case resolved", "success");
      queryClient.invalidateQueries({ queryKey: ["hr-case", id] });
      queryClient.invalidateQueries({ queryKey: ["hr-cases"] });
    },
  });

  if (caseQ.isLoading) {
    return (
      <div className="page">
        <div style={{ padding: 40, color: "var(--text-3)" }}>Loading…</div>
      </div>
    );
  }
  const c = caseQ.data;
  if (!c) {
    return (
      <div className="page">
        <Button variant="ghost" size="sm" onClick={() => navigate("/hr-cases")}>← Back</Button>
        <div className="empty">
          <div className="title">Case not found</div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <Button
        variant="ghost"
        size="sm"
        style={{ marginBottom: 16 }}
        onClick={() => navigate("/hr-cases")}
      >
        <I.chevron size={14} style={{ transform: "rotate(180deg)" }} /> Back to HR cases
      </Button>
      <div className="grid" style={{ gridTemplateColumns: "1.6fr 1fr", gap: 20 }}>
        <Card>
          <div style={{ padding: 24 }}>
            <span className="eyebrow">{c.case_number || c.id.slice(0, 8)}</span>
            <h1 style={{ fontSize: 30, color: "var(--ink-3)", margin: "8px 0" }}>{c.subject}</h1>
            <div
              style={{
                display: "flex",
                gap: 14,
                fontSize: 13,
                color: "var(--text-2)",
                marginBottom: 20,
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <PersonCell name={c.raised_by_name || "—"} size="sm" />
              <Badge tone="outline">{c.category_name || c.category}</Badge>
              <Badge tone={c.priority === "high" ? "red" : c.priority === "low" ? "soft" : "blue"} dot>
                {c.priority}
              </Badge>
              <StatusBadge status={c.status_display || c.status} />
            </div>

            <div
              style={{
                background: "var(--card-2)",
                border: "1px solid var(--hairline-2)",
                borderRadius: 12,
                padding: 16,
                marginBottom: 20,
                fontSize: 13.5,
                color: "var(--text-2)",
                lineHeight: 1.55,
              }}
            >
              {c.description}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 20 }}>
              {(commentsQ.data || []).map((m) => (
                <div key={m.id} style={{ display: "flex", gap: 12 }}>
                  <Avatar name={m.author_name || "?"} />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>
                        {m.author_name || "—"}
                        {m.is_internal && (
                          <Badge tone="yellow" style={{ marginLeft: 6, fontSize: 10 }}>
                            Internal
                          </Badge>
                        )}
                      </span>
                      <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>
                        {m.created_at?.slice(0, 16).replace("T", " ")}
                      </span>
                    </div>
                    <div
                      style={{
                        padding: 12,
                        background: m.is_internal ? "var(--yellow-soft)" : "var(--card)",
                        border: "1px solid var(--hairline-2)",
                        borderRadius: 10,
                        fontSize: 13,
                        color: "var(--text-2)",
                        lineHeight: 1.55,
                      }}
                    >
                      {m.body}
                    </div>
                  </div>
                </div>
              ))}
              {(commentsQ.data || []).length === 0 && commentsQ.isFetched && (
                <div style={{ fontSize: 13, color: "var(--text-3)" }}>
                  No messages on this thread yet.
                </div>
              )}
            </div>

            <div style={{ borderTop: "1px solid var(--hairline-2)", paddingTop: 14 }}>
              <textarea
                className="textarea"
                placeholder="Reply..."
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
              />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
                <label className="checkbox">
                  <input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} />
                  Internal note
                </label>
                <div style={{ display: "flex", gap: 6 }}>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setStatus.mutate("awaiting_employee")}
                  >
                    Awaiting employee
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    leftIcon={<I.send size={13} />}
                    disabled={reply.isPending || !draft.trim()}
                    onClick={() => reply.mutate()}
                  >
                    Send
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </Card>

        <div className="col" style={{ gap: 16 }}>
          <Card>
            <CardHead title="Details" />
            <div className="card-body" style={{ paddingTop: 4 }}>
              {[
                { l: "Status", v: <StatusBadge status={c.status_display || c.status} /> },
                { l: "Priority", v: c.priority },
                { l: "Category", v: c.category_name || c.category },
                { l: "Assignee", v: c.assignee_name || "Unassigned" },
                { l: "SLA due", v: c.sla_due_at?.slice(0, 10) || "—" },
                { l: "Updated", v: c.updated_at?.slice(0, 16).replace("T", " ") || "—" },
              ].map((row, i, arr) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "8px 0",
                    borderBottom: i === arr.length - 1 ? "none" : "1px solid var(--hairline-2)",
                    fontSize: 13,
                  }}
                >
                  <span style={{ color: "var(--text-3)" }}>{row.l}</span>
                  <span style={{ fontWeight: 500 }}>{row.v}</span>
                </div>
              ))}
            </div>
          </Card>
          <Card>
            <CardHead title="Actions" />
            <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {!c.assignee && (
                <Button
                  variant="primary"
                  size="sm"
                  disabled={takeOwnership.isPending}
                  onClick={() => takeOwnership.mutate()}
                >
                  Take ownership
                </Button>
              )}
              {c.status !== "resolved" && (
                <Button
                  variant="primary"
                  size="sm"
                  leftIcon={<I.check size={13} />}
                  disabled={resolveMut.isPending}
                  onClick={() => resolveMut.mutate()}
                >
                  Mark resolved
                </Button>
              )}
              {c.status === "resolved" && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setStatus.mutate("open")}
                >
                  Reopen
                </Button>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
