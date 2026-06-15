import { useMemo, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Avatar,
  Badge,
  BarChart,
  Button,
  Card,
  CardHead,
  Donut,
  KpiCell,
  KpiStrip,
  Modal,
  PageHeader,
  Pagination,
  Stars,
  StatusBadge,
  Tabs,
  useToast,
  usePaginated,
} from "@/components/ui";
import { downloadCsv } from "@/lib/export";
import { fmtDate } from "@/lib/format";
import { useAuth } from "@/store/auth";
import { listDepartments } from "@/api/organisation";
import {
  createCandidate,
  createJobRequisition,
  listCandidates,
  listJobPostings,
  listJobRequisitions,
  moveCandidateStage,
  type Candidate,
} from "@/api/hr";

const STAGES: Array<{ value: string; label: string; color: string }> = [
  { value: "applied", label: "Applied", color: "var(--text-3)" },
  { value: "screening", label: "Screening", color: "var(--bunchly)" },
  { value: "shortlisted", label: "Shortlisted", color: "var(--action)" },
  { value: "interview", label: "Interview", color: "var(--action-deep)" },
  { value: "reference_check", label: "Reference check", color: "#7B5BFF" },
  { value: "offer", label: "Offer", color: "var(--yellow-deep)" },
  { value: "hired", label: "Hired", color: "var(--positive)" },
];

function stageLabel(value: string) {
  return STAGES.find((s) => s.value === value)?.label || value;
}
function stageColor(value: string) {
  return STAGES.find((s) => s.value === value)?.color || "var(--text-3)";
}

function CandidateCard({
  c,
  onClick,
  onMove,
  isMoving,
  canMove,
}: {
  c: Candidate;
  onClick: () => void;
  onMove: (stage: string) => void;
  isMoving: boolean;
  canMove: boolean;
}) {
  const days = c.applied_at
    ? Math.max(0, Math.floor((Date.now() - new Date(c.applied_at).getTime()) / 86_400_000))
    : 0;
  return (
    <div
      style={{
        background: "var(--card)",
        border: "1px solid var(--hairline)",
        borderRadius: 10,
        padding: 10,
        transition: "transform 0.08s, box-shadow 0.1s",
        boxShadow: "0 1px 0 rgba(20,30,44,0.04)",
        opacity: isMoving ? 0.6 : 1,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = "translateY(-1px)";
        e.currentTarget.style.boxShadow = "0 4px 12px rgba(20,30,44,0.08)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = "";
        e.currentTarget.style.boxShadow = "0 1px 0 rgba(20,30,44,0.04)";
      }}
    >
      <div style={{ display: "flex", gap: 8, cursor: "pointer" }} onClick={onClick}>
        <Avatar name={c.full_name || c.email || "?"} size="sm" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-3)" }}>
            {c.full_name || `${c.first_name || ""} ${c.last_name || ""}`}
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
            {c.posting_title || "—"}
          </div>
        </div>
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 8,
          fontSize: 11,
          color: "var(--text-3)",
        }}
      >
        <span>
          <I.clock size={11} style={{ verticalAlign: "-1px", marginRight: 3 }} />
          {days}d
        </span>
        <Stars value={c.rating != null ? Number(c.rating) : null} />
      </div>
      {canMove && (
        <select
          value=""
          onChange={(e) => e.target.value && onMove(e.target.value)}
          onClick={(e) => e.stopPropagation()}
          className="select"
          disabled={isMoving}
          style={{ marginTop: 8, height: 26, fontSize: 11, padding: "0 8px" }}
        >
          <option value="">Move to…</option>
          {STAGES.map((s) => (
            <option key={s.value} value={s.value} disabled={s.value === c.stage}>
              {s.label}
            </option>
          ))}
          <option value="rejected">Rejected</option>
        </select>
      )}
    </div>
  );
}

function NewRequisitionModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const departments = useQuery({
    queryKey: ["departments"],
    queryFn: listDepartments,
    enabled: open,
  });
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [headcount, setHeadcount] = useState(1);
  const [employmentType, setEmploymentType] = useState("full_time");
  const [reason, setReason] = useState("");

  const create = useMutation({
    mutationFn: createJobRequisition,
    onSuccess: (rec) => {
      toast.push(`Requisition ${rec.reference || rec.id.slice(0, 6)} saved`, "success");
      queryClient.invalidateQueries({ queryKey: ["job-requisitions"] });
      onClose();
      setTitle("");
      setReason("");
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not save requisition",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      toast.push("Title is required", "error");
      return;
    }
    create.mutate({
      title: title.trim(),
      department: department || undefined,
      headcount,
      employment_type: employmentType,
      reason: reason.trim() || undefined,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New requisition"
      sub="Define the role; an approved requisition can then be published as a posting."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={create.isPending}>
            {create.isPending ? "Saving…" : "Save draft"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="grid grid-2" style={{ gap: 14 }}>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Role title</label>
            <input
              className="input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Senior Backend Engineer"
              autoFocus
            />
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
            <label>Headcount</label>
            <input
              className="input"
              type="number"
              min={1}
              value={headcount}
              onChange={(e) => setHeadcount(Number(e.target.value) || 1)}
            />
          </div>
          <div className="field">
            <label>Employment type</label>
            <select className="select" value={employmentType} onChange={(e) => setEmploymentType(e.target.value)}>
              <option value="full_time">Full-time</option>
              <option value="part_time">Part-time</option>
              <option value="contract">Contract</option>
              <option value="intern">Intern</option>
            </select>
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Reason</label>
            <textarea
              className="textarea"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why we need this role."
            />
          </div>
        </div>
      </form>
    </Modal>
  );
}

function NewCandidateModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const postings = useQuery({
    queryKey: ["job-postings"],
    queryFn: () => listJobPostings(),
    enabled: open,
  });
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [posting, setPosting] = useState("");
  const [source, setSource] = useState("careers_page");

  const create = useMutation({
    mutationFn: createCandidate,
    onSuccess: () => {
      toast.push("Candidate added", "success");
      queryClient.invalidateQueries({ queryKey: ["candidates"] });
      onClose();
      setFirstName("");
      setLastName("");
      setEmail("");
      setPhone("");
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not add candidate",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!firstName.trim() || !lastName.trim() || !email.trim()) {
      toast.push("Name and email are required", "error");
      return;
    }
    create.mutate({
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      email: email.trim(),
      phone: phone.trim() || undefined,
      posting: posting || undefined,
      source,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add candidate"
      sub="Lands in the Applied column."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={create.isPending}>
            {create.isPending ? "Adding…" : "Add candidate"}
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
            <label>Email</label>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label>Phone</label>
            <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
          <div className="field">
            <label>Posting</label>
            <select className="select" value={posting} onChange={(e) => setPosting(e.target.value)}>
              <option value="">{postings.isLoading ? "Loading…" : "No posting"}</option>
              {(postings.data?.results ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Source</label>
            <select className="select" value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="careers_page">Careers page</option>
              <option value="linkedin">LinkedIn</option>
              <option value="referral">Referral</option>
              <option value="recruiter">Recruiter</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>
      </form>
    </Modal>
  );
}

function PipelineBoard({
  filterPosting,
  setFilterPosting,
  canManage,
}: {
  filterPosting: string;
  setFilterPosting: (v: string) => void;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();
  const candidates = useQuery({
    queryKey: ["candidates"],
    queryFn: () => listCandidates(),
  });
  const postings = useQuery({
    queryKey: ["job-postings"],
    queryFn: () => listJobPostings(),
  });

  const move = useMutation({
    mutationFn: (vars: { id: string; stage: string }) =>
      moveCandidateStage(vars.id, vars.stage),
    onSuccess: (cand, vars) => {
      toast.push(`Moved to ${stageLabel(vars.stage)}`, "success");
      queryClient.invalidateQueries({ queryKey: ["candidates"] });
      void cand;
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not move stage",
        "error",
      ),
  });

  const rows = candidates.data?.results ?? [];
  const filtered =
    filterPosting === "all" ? rows : rows.filter((c) => c.posting === filterPosting);

  return (
    <>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center" }}>
        <select
          className="select"
          style={{ height: 34, width: 260 }}
          value={filterPosting}
          onChange={(e) => setFilterPosting(e.target.value)}
        >
          <option value="all">All postings</option>
          {(postings.data?.results ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.title}
            </option>
          ))}
        </select>
        <div style={{ marginLeft: "auto", fontSize: 12.5, color: "var(--text-3)" }}>
          {candidates.isLoading
            ? "Loading…"
            : `${filtered.length} candidates · use the stage selector on each card`}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${STAGES.length}, minmax(220px, 1fr))`,
          gap: 12,
          overflowX: "auto",
        }}
      >
        {STAGES.map((stage) => {
          const inStage = filtered.filter((c) => c.stage === stage.value);
          return (
            <div
              key={stage.value}
              style={{
                background: "var(--card-2)",
                border: "1px solid var(--hairline)",
                borderRadius: 12,
                padding: 10,
                minHeight: 480,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "4px 6px 10px",
                  borderBottom: `2px solid ${stage.color}`,
                  marginBottom: 10,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ width: 7, height: 7, borderRadius: 50, background: stage.color }} />
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{stage.label}</span>
                </div>
                <span
                  style={{
                    fontSize: 11,
                    fontVariantNumeric: "tabular-nums",
                    color: "var(--text-3)",
                    background: "var(--card)",
                    padding: "1px 8px",
                    borderRadius: 999,
                    border: "1px solid var(--hairline)",
                  }}
                >
                  {inStage.length}
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {inStage.map((c) => (
                  <CandidateCard
                    key={c.id}
                    c={c}
                    onClick={() => navigate(`/recruitment/${c.id}`)}
                    onMove={(s) => move.mutate({ id: c.id, stage: s })}
                    isMoving={move.isPending && move.variables?.id === c.id}
                    canMove={canManage}
                  />
                ))}
                {inStage.length === 0 && (
                  <div
                    style={{
                      padding: 16,
                      textAlign: "center",
                      fontSize: 12,
                      color: "var(--text-3)",
                      border: "1px dashed var(--hairline)",
                      borderRadius: 8,
                    }}
                  >
                    No candidates
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

function RequisitionsTable() {
  const reqs = useQuery({
    queryKey: ["job-requisitions"],
    queryFn: () => listJobRequisitions(),
  });
  const rows = reqs.data?.results ?? [];
  const pag = usePaginated(rows);

  return (
    <Card>
      <table className="table">
        <thead>
          <tr>
            <th>Role</th>
            <th>Reference</th>
            <th>Department</th>
            <th>Headcount</th>
            <th>Type</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {pag.slice.map((r) => (
            <tr key={r.id}>
              <td>
                <div style={{ fontWeight: 600 }}>{r.title}</div>
                <div style={{ fontSize: 11.5, color: "var(--text-3)" }}>{r.reason || "—"}</div>
              </td>
              <td className="num" style={{ fontFamily: "var(--mono)", fontSize: 12 }}>
                {r.reference || "—"}
              </td>
              <td>{r.department_name || "—"}</td>
              <td className="num">{r.headcount}</td>
              <td>
                <Badge tone="outline">{r.employment_type}</Badge>
              </td>
              <td>
                <StatusBadge status={r.status_display || r.status} />
              </td>
              <td className="muted num">{r.created_at ? fmtDate(r.created_at) : "—"}</td>
            </tr>
          ))}
          {rows.length === 0 && reqs.isFetched && (
            <tr>
              <td colSpan={7}>
                <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                  No requisitions yet.
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

function JobPostingsView() {
  const postings = useQuery({
    queryKey: ["job-postings"],
    queryFn: () => listJobPostings(),
  });
  const rows = postings.data?.results ?? [];
  const toast = useToast();

  if (postings.isLoading) {
    return (
      <Card>
        <div style={{ padding: 28, color: "var(--text-3)" }}>Loading…</div>
      </Card>
    );
  }

  if (rows.length === 0) {
    return (
      <Card>
        <div className="empty">
          <div className="title">No postings yet</div>
          <div className="lede">Approve a requisition and publish a posting to see it here.</div>
        </div>
      </Card>
    );
  }

  return (
    <div className="grid grid-2">
      {rows.map((p) => (
        <Card key={p.id}>
          <div style={{ padding: 20 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: 6,
              }}
            >
              <Badge tone="blue" dot>{p.location_name || "Anywhere"}</Badge>
              <Badge tone={p.status === "open" ? "green" : "outline"} dot>
                {p.status_display || p.status}
              </Badge>
            </div>
            <h3 style={{ fontSize: 22, color: "var(--ink-3)", margin: "8px 0 4px" }}>{p.title}</h3>
            <div style={{ color: "var(--text-2)", fontSize: 13 }}>
              {p.employment_type || "—"} · {p.candidate_count ?? 0} candidate
              {(p.candidate_count ?? 0) === 1 ? "" : "s"}
            </div>
            <div className="divider" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 12.5 }}>
              <div>
                <div style={{ color: "var(--text-3)" }}>Posted</div>
                <div style={{ fontWeight: 500 }}>{p.posted_date ? fmtDate(p.posted_date) : "—"}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-3)" }}>Closes</div>
                <div style={{ fontWeight: 500 }}>{p.closing_date ? fmtDate(p.closing_date) : "—"}</div>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
              <Button
                variant="outline"
                size="sm"
                leftIcon={<I.link size={13} />}
                onClick={() => {
                  const url = `https://careers.bunchly.io/${p.id}`;
                  navigator.clipboard?.writeText(url);
                  toast.push("Posting URL copied", "success");
                }}
              >
                Copy link
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

function RecruitmentAnalytics({ candidates }: { candidates: Candidate[] }) {
  const bySource = useMemo(() => {
    const m = new Map<string, number>();
    for (const c of candidates) {
      const k = c.source || "other";
      m.set(k, (m.get(k) || 0) + 1);
    }
    const colors = ["var(--action)", "var(--yellow)", "var(--bunchly)", "var(--ink-3)", "var(--text-4)"];
    return Array.from(m.entries()).map(([k, n], i) => ({
      label: k,
      n,
      color: colors[i % colors.length],
    }));
  }, [candidates]);
  const totalHires = candidates.filter((c) => c.stage === "hired").length;

  return (
    <div className="grid grid-2">
      <Card>
        <CardHead title="Pipeline funnel" sub="Live counts from the board" />
        <div className="card-body">
          <BarChart
            data={STAGES.map((s, i) => ({
              label: s.label,
              value: candidates.filter((c) => c.stage === s.value).length,
              color:
                i === 0
                  ? "var(--text-3)"
                  : i === STAGES.length - 1
                    ? "var(--positive)"
                    : "var(--action)",
            }))}
          />
        </div>
      </Card>
      <Card>
        <CardHead title="Sources" sub="Where candidates came from" />
        <div className="card-body" style={{ display: "flex", gap: 32, alignItems: "center" }}>
          <Donut
            size={160}
            segments={bySource.length > 0 ? bySource.map((s) => ({ value: s.n, color: s.color })) : [{ value: 1, color: "var(--hairline)" }]}
            label={String(totalHires)}
            sub="hires"
          />
          <div style={{ flex: 1, fontSize: 13 }}>
            {bySource.length === 0 ? (
              <div style={{ color: "var(--text-3)" }}>No data yet.</div>
            ) : (
              bySource.map((s, i, arr) => (
                <div
                  key={s.label}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "6px 0",
                    borderBottom: i === arr.length - 1 ? "none" : "1px solid var(--hairline-2)",
                  }}
                >
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 3, background: s.color }} /> {s.label}
                  </span>
                  <span style={{ fontVariantNumeric: "tabular-nums", color: "var(--text-3)" }}>{s.n}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}

export default function RecruitmentPage() {
  const { hasPerm } = useAuth();
  const canManage = hasPerm("recruitment.manage");
  const [tab, setTab] = useState("pipeline");
  const [filterPosting, setFilterPosting] = useState("all");
  const [showNewReq, setShowNewReq] = useState(false);
  const [showNewCand, setShowNewCand] = useState(false);

  const candidates = useQuery({
    queryKey: ["candidates"],
    queryFn: () => listCandidates(),
  });
  const reqs = useQuery({
    queryKey: ["job-requisitions"],
    queryFn: () => listJobRequisitions(),
  });
  const candList = candidates.data?.results ?? [];
  const reqList = reqs.data?.results ?? [];

  const hired = candList.filter((c) => c.stage === "hired").length;
  const offers = candList.filter((c) => c.stage === "offer").length;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Talent acquisition"
        title="Recruitment"
        lede={
          candidates.isLoading || reqs.isLoading
            ? "Loading…"
            : `${reqList.filter((r) => r.status === "approved").length} approved reqs · ${candList.length} candidates`
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={() =>
                downloadCsv(
                  `candidates-${new Date().toISOString().slice(0, 10)}.csv`,
                  candList,
                )
              }
            >
              Export
            </Button>
            {canManage && (
              <>
                <Button variant="outline" size="sm" leftIcon={<I.plus size={14} />} onClick={() => setShowNewCand(true)}>
                  Add candidate
                </Button>
                <Button variant="primary" size="sm" leftIcon={<I.plus size={14} />} onClick={() => setShowNewReq(true)}>
                  New requisition
                </Button>
              </>
            )}
          </>
        }
      />
      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="Requisitions" value={reqList.length} sub="All states" />
        <KpiCell label="Candidates in flight" value={candList.filter((c) => !["hired", "rejected"].includes(c.stage)).length} />
        <KpiCell label="Outstanding offers" value={offers} />
        <KpiCell label="Hired" value={hired} />
      </KpiStrip>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "pipeline", label: "Pipeline", count: candList.length },
          { value: "reqs", label: "Requisitions", count: reqList.length },
          { value: "postings", label: "Job postings" },
          { value: "analytics", label: "Analytics" },
        ]}
      />
      {tab === "pipeline" && (
        <PipelineBoard
          filterPosting={filterPosting}
          setFilterPosting={setFilterPosting}
          canManage={canManage}
        />
      )}
      {tab === "reqs" && <RequisitionsTable />}
      {tab === "postings" && <JobPostingsView />}
      {tab === "analytics" && <RecruitmentAnalytics candidates={candList} />}

      <NewRequisitionModal open={showNewReq} onClose={() => setShowNewReq(false)} />
      <NewCandidateModal open={showNewCand} onClose={() => setShowNewCand(false)} />
    </div>
  );
}

export function CandidateDetailPage() {
  const navigate = useNavigate();
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { hasPerm } = useAuth();
  const canManage = hasPerm("recruitment.manage");

  const candidates = useQuery({
    queryKey: ["candidates"],
    queryFn: () => listCandidates(),
  });
  const c = (candidates.data?.results ?? []).find((x) => x.id === id);

  const move = useMutation({
    mutationFn: (stage: string) => moveCandidateStage(id, stage),
    onSuccess: (_data, stage) => {
      toast.push(`Moved to ${stageLabel(stage)}`, "success");
      queryClient.invalidateQueries({ queryKey: ["candidates"] });
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not move stage",
        "error",
      ),
  });

  if (candidates.isLoading) {
    return (
      <div className="page">
        <div style={{ padding: 40, color: "var(--text-3)" }}>Loading…</div>
      </div>
    );
  }

  if (!c) {
    return (
      <div className="page">
        <Button variant="ghost" size="sm" onClick={() => navigate("/recruitment")}>
          ← Back
        </Button>
        <div className="empty">
          <div className="title">Candidate not found</div>
        </div>
      </div>
    );
  }

  const currIdx = STAGES.findIndex((s) => s.value === c.stage);

  return (
    <div className="page">
      <Button variant="ghost" size="sm" style={{ marginBottom: 16 }} onClick={() => navigate("/recruitment")}>
        <I.chevron size={14} style={{ transform: "rotate(180deg)" }} /> Back to Recruitment
      </Button>
      <Card>
        <div style={{ padding: 24 }}>
          <div style={{ display: "flex", gap: 16 }}>
            <Avatar name={c.full_name || c.email || "?"} size="xl" />
            <div style={{ flex: 1 }}>
              <span className="eyebrow" style={{ fontFamily: "var(--mono)" }}>
                {c.id.slice(0, 8)}
              </span>
              <h1 style={{ fontSize: 32, color: "var(--ink-3)", margin: "4px 0" }}>
                {c.full_name || `${c.first_name || ""} ${c.last_name || ""}`}
              </h1>
              <div style={{ color: "var(--text-2)" }}>{c.posting_title || "—"}</div>
              <div style={{ display: "flex", gap: 14, fontSize: 12.5, color: "var(--text-3)", marginTop: 10 }}>
                {c.email && <span>{c.email}</span>}
                {c.phone && <span>{c.phone}</span>}
                {c.source && <span>· via {c.source}</span>}
              </div>
            </div>
            {canManage && (
              <div style={{ display: "flex", gap: 6 }}>
                <select
                  className="select"
                  value=""
                  onChange={(e) => e.target.value && move.mutate(e.target.value)}
                  style={{ height: 32 }}
                  disabled={move.isPending}
                >
                  <option value="">Move stage…</option>
                  {STAGES.map((s) => (
                    <option key={s.value} value={s.value} disabled={s.value === c.stage}>
                      {s.label}
                    </option>
                  ))}
                  <option value="rejected">Rejected</option>
                </select>
              </div>
            )}
          </div>
          <div className="divider" />
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
            {STAGES.map((s, i) => {
              const done = i < currIdx;
              const active = i === currIdx;
              return (
                <div key={s.value} style={{ flex: 1, textAlign: "center" }}>
                  <div
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: 50,
                      margin: "0 auto",
                      background: done
                        ? "var(--positive)"
                        : active
                          ? stageColor(s.value)
                          : "var(--hairline)",
                      color: done || active ? "#fff" : "var(--text-3)",
                      display: "grid",
                      placeItems: "center",
                      fontSize: 11,
                      fontWeight: 700,
                    }}
                  >
                    {done ? "✓" : i + 1}
                  </div>
                  <div
                    style={{
                      fontSize: 10.5,
                      color: active ? "var(--ink-3)" : "var(--text-3)",
                      marginTop: 4,
                      fontWeight: active ? 600 : 400,
                    }}
                  >
                    {s.label}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Card>

      {c.notes && (
        <Card style={{ marginTop: 20 }}>
          <CardHead title="Notes" />
          <div className="card-body" style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>
            {c.notes}
          </div>
        </Card>
      )}
    </div>
  );
}
