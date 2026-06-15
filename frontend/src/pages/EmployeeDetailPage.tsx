import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardHead,
  CardBody,
  Empty,
  FileRow,
  Meter,
  Modal,
  PageHeader,
  Stars,
  StatusBadge,
  Tabs,
  useToast,
} from "@/components/ui";
import { ContractsPanel } from "@/features/contracts/ContractsPanel";
import {
  getEmployee,
  updateEmployee,
  type EmployeeDetail,
} from "@/api/employees";
import { listDocuments } from "@/api/documents";
import {
  listLeaveBalances,
  listLeaveRequests,
  type LeaveBalance,
  type LeaveRequest,
} from "@/api/leave";
import {
  listAuditLog,
  listPerformanceReviews,
  listTrainingRecords,
} from "@/api/hr";
import {
  listDepartments,
  listJobTitles,
  listLocations,
} from "@/api/organisation";
import { fmtDate } from "@/lib/format";
import { useAuth } from "@/store/auth";

/* Stable pastel avatar slot per name (kept here so chart/card colours
   don't depend on a value we'd have to store on the backend). */
function avFor(name: string): string {
  let hash = 0;
  for (let i = 0; i < (name || "").length; i++) hash = (hash * 31 + name.charCodeAt(i)) | 0;
  return `av-${(Math.abs(hash) % 8) + 1}`;
}

function statusLabel(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ") : "—";
}

function Mini({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div>
      <div
        style={{
          fontSize: 11,
          textTransform: "uppercase",
          color: "var(--text-3)",
          letterSpacing: "0.08em",
          fontWeight: 600,
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: 22, color: "var(--ink-3)", marginTop: 2, letterSpacing: "-0.01em" }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function KV({
  label,
  value,
  confidential,
}: {
  label: ReactNode;
  value: ReactNode;
  confidential?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        padding: "8px 0",
        borderBottom: "1px solid var(--hairline-2)",
        fontSize: 13,
      }}
    >
      <span style={{ color: "var(--text-3)" }}>{label}</span>
      <span style={{ color: "var(--text)", fontWeight: 500 }}>
        {confidential && (
          <I.shield
            size={11}
            style={{ verticalAlign: "-1px", color: "var(--text-3)", marginRight: 4 }}
          />
        )}
        {value ?? "—"}
      </span>
    </div>
  );
}

function tenureSummary(startDate: string | undefined): string {
  if (!startDate) return "—";
  const start = new Date(startDate);
  if (Number.isNaN(start.getTime())) return "—";
  const now = new Date();
  const months =
    (now.getFullYear() - start.getFullYear()) * 12 + (now.getMonth() - start.getMonth());
  const years = Math.floor(months / 12);
  const rem = months % 12;
  if (years === 0) return `${months} mo`;
  if (rem === 0) return `${years} yr${years === 1 ? "" : "s"}`;
  return `${years} yr${years === 1 ? "" : "s"} ${rem} mo`;
}

export default function EmployeeDetailPage() {
  const navigate = useNavigate();
  const { id = "" } = useParams();
  const { hasPerm } = useAuth();

  const employeeQ = useQuery({
    queryKey: ["employee", id],
    queryFn: () => getEmployee(id),
    enabled: !!id,
  });

  const [tab, setTab] = useState("overview");
  const [showEdit, setShowEdit] = useState(false);
  const toast = useToast();

  if (employeeQ.isLoading) {
    return (
      <div className="page">
        <PageHeader title="Employee" lede="Loading…" />
      </div>
    );
  }
  if (employeeQ.isError || !employeeQ.data) {
    return (
      <div className="page">
        <Button
          variant="ghost"
          size="sm"
          style={{ marginBottom: 16 }}
          onClick={() => navigate("/people")}
        >
          <I.chevron size={14} style={{ transform: "rotate(180deg)" }} /> Back to People
        </Button>
        <Card>
          <div className="empty" style={{ margin: 16 }}>
            <div className="title">Employee not found</div>
            <div className="lede">
              We couldn't load this record. They may have been archived, or you may not
              have access.
            </div>
          </div>
        </Card>
      </div>
    );
  }

  const e = employeeQ.data;
  const name = e.full_name || `${e.first_name ?? ""} ${e.last_name ?? ""}`.trim();
  const titleLine = [e.job_title_name, e.department_name].filter(Boolean).join(" · ");
  const email = e.work_email || e.email || e.personal_email || "";

  return (
    <div className="page">
      <Button
        variant="ghost"
        size="sm"
        style={{ marginBottom: 16 }}
        onClick={() => navigate("/people")}
      >
        <I.chevron size={14} style={{ transform: "rotate(180deg)" }} /> Back to People
      </Button>

      <Card>
        <div
          style={{
            padding: "28px 28px 22px",
            display: "flex",
            gap: 24,
            alignItems: "flex-start",
          }}
        >
          <Avatar name={name} av={avFor(name)} size="xl" />
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 4 }}>
              <span className="eyebrow">{e.employee_number || e.employee_code || e.id.slice(0, 8)}</span>
              <StatusBadge status={statusLabel(e.employment_status)} />
              {e.employment_status === "probation" && (
                <Badge tone="yellow" dot>
                  On probation
                </Badge>
              )}
              {e.contract_end_date && (
                <Badge tone="blue" dot>
                  Contract ends {fmtDate(e.contract_end_date)}
                </Badge>
              )}
            </div>
            <h1
              style={{
                fontSize: 36,
                color: "var(--ink-3)",
                margin: "0 0 4px",
                letterSpacing: "-0.015em",
              }}
            >
              {name || "—"}
            </h1>
            <div style={{ color: "var(--text-2)", fontSize: 15 }}>{titleLine || "—"}</div>
            <div
              style={{
                display: "flex",
                gap: 18,
                marginTop: 14,
                fontSize: 13,
                color: "var(--text-2)",
                flexWrap: "wrap",
              }}
            >
              {email && (
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <I.mail size={14} /> {email}
                </span>
              )}
              {e.work_location_name && (
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <I.pin size={14} /> {e.work_location_name}
                </span>
              )}
              {e.start_date && (
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <I.briefcase size={14} /> Joined {fmtDate(e.start_date)}
                </span>
              )}
              {e.line_manager_name && (
                <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <I.user size={14} /> Reports to {e.line_manager_name}
                </span>
              )}
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.message size={14} />}
              onClick={() =>
                navigate(
                  `/hr-cases?subject=${encodeURIComponent(`Message for ${name}`)}`,
                )
              }
            >
              Message
            </Button>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.mail size={14} />}
              onClick={() => {
                if (!email) {
                  toast.push("No email on file", "error");
                  return;
                }
                window.location.href = `mailto:${email}?subject=${encodeURIComponent(
                  `Hi ${name.split(" ")[0]}`,
                )}`;
              }}
            >
              Email
            </Button>
            {hasPerm("employees.change_employee") && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.edit size={14} />}
                onClick={() => setShowEdit(true)}
              >
                Edit profile
              </Button>
            )}
          </div>
        </div>
        <div style={{ borderTop: "1px solid var(--hairline-2)", padding: "0 24px" }}>
          <Tabs
            value={tab}
            onChange={setTab}
            items={[
              { value: "overview", label: "Overview" },
              { value: "employment", label: "Employment" },
              { value: "leave", label: "Leave" },
              { value: "documents", label: "Documents" },
              { value: "compensation", label: "Compensation" },
              { value: "performance", label: "Performance" },
              { value: "training", label: "Training" },
              { value: "history", label: "History" },
              { value: "contracts", label: "Contracts" },
            ]}
          />
        </div>
      </Card>

      {tab === "overview" && <OverviewTab employee={e} />}
      {tab === "employment" && <EmploymentTab employee={e} />}
      {tab === "leave" && <LeaveTab employeeId={e.id} />}
      {tab === "documents" && <DocsTab employeeId={e.id} />}
      {tab === "compensation" && <CompTab employee={e} />}
      {tab === "performance" && <PerfTab employeeId={e.id} />}
      {tab === "training" && <TrainingTab employeeId={e.id} />}
      {tab === "history" && <HistoryTab employee={e} />}
      {tab === "contracts" && <ContractsPanel employeeId={e.id} />}

      <EditProfileModal
        open={showEdit}
        onClose={() => setShowEdit(false)}
        employee={e}
      />
    </div>
  );
}

/* ---------------------------------------------------------------- *
 * Edit profile — PATCH against /employees/:id/
 *
 * Sensitive PII fields (national_id, passport_number) are intentionally
 * excluded here — they're handled by the backend's masking layer and
 * editing them belongs in a dedicated, audited flow gated on
 * `employees.view_pii`.
 * ---------------------------------------------------------------- */
function SectionHeading({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        gridColumn: "1 / -1",
        fontSize: 11,
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        fontWeight: 600,
        color: "var(--text-3)",
        marginTop: 8,
        marginBottom: -4,
      }}
    >
      {children}
    </div>
  );
}

function EditProfileModal({
  open,
  onClose,
  employee,
}: {
  open: boolean;
  onClose: () => void;
  employee: EmployeeDetail;
}) {
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
  const locations = useQuery({
    queryKey: ["locations"],
    queryFn: listLocations,
    enabled: open,
  });

  /* Identity */
  const [first, setFirst] = useState(employee.first_name || "");
  const [last, setLast] = useState(employee.last_name || "");
  const [preferred, setPreferred] = useState(employee.preferred_name || "");
  const [gender, setGender] = useState(employee.gender || "");
  const [dob, setDob] = useState(employee.date_of_birth || "");
  const [marital, setMarital] = useState(employee.marital_status || "");

  /* Contact */
  const [workEmail, setWorkEmail] = useState(employee.work_email || "");
  const [personalEmail, setPersonalEmail] = useState(employee.personal_email || "");
  const [phone, setPhone] = useState(employee.phone || "");
  const [altPhone, setAltPhone] = useState(employee.alternate_phone || "");

  /* Address */
  const [addr1, setAddr1] = useState(employee.address_line1 || "");
  const [addr2, setAddr2] = useState(employee.address_line2 || "");
  const [city, setCity] = useState(employee.city || "");
  const [state, setState] = useState(employee.state || "");
  const [postal, setPostal] = useState(employee.postal_code || "");
  const [country, setCountry] = useState(employee.country || "");

  /* Employment */
  const [title, setTitle] = useState<string>(employee.job_title || "");
  const [dept, setDept] = useState<string>(employee.department || "");
  const [loc, setLoc] = useState<string>(employee.work_location || "");
  const [type, setType] = useState(employee.employment_type || "permanent");

  /* Empty-string -> null keeps the backend happy on optional FKs + char
     fields that are nullable. Trimming defends against incidental spaces. */
  const opt = (v: string) => {
    const t = v.trim();
    return t === "" ? null : t;
  };

  const mutation = useMutation({
    mutationFn: () =>
      updateEmployee(employee.id, {
        first_name: first.trim(),
        last_name: last.trim(),
        preferred_name: opt(preferred),
        gender: opt(gender),
        date_of_birth: opt(dob),
        marital_status: opt(marital),
        work_email: opt(workEmail),
        personal_email: opt(personalEmail),
        phone: opt(phone),
        alternate_phone: opt(altPhone),
        address_line1: opt(addr1),
        address_line2: opt(addr2),
        city: opt(city),
        state: opt(state),
        postal_code: opt(postal),
        country: opt(country),
        job_title: title || null,
        department: dept || null,
        work_location: loc || null,
        employment_type: type,
      }),
    onSuccess: () => {
      toast.push("Profile updated", "success");
      queryClient.invalidateQueries({ queryKey: ["employee", employee.id] });
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      onClose();
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data;
      const firstKey = data && Object.keys(data)[0];
      const msg =
        firstKey && Array.isArray(data?.[firstKey])
          ? `${firstKey}: ${(data[firstKey] as string[])[0]}`
          : (data as { detail?: string })?.detail || "Could not save changes";
      toast.push(msg, "error");
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!first.trim() || !last.trim()) {
      toast.push("First and last name are required", "error");
      return;
    }
    mutation.mutate();
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      width={720}
      title={`Edit profile · ${employee.full_name}`}
      sub="Sensitive fields (National ID / passport / bank) live in a separate, audited flow."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Saving…" : "Save changes"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="grid grid-2" style={{ gap: 14 }}>
          <SectionHeading>Identity</SectionHeading>
          <div className="field">
            <label>First name</label>
            <input
              className="input"
              value={first}
              onChange={(e) => setFirst(e.target.value)}
              autoFocus
            />
          </div>
          <div className="field">
            <label>Last name</label>
            <input
              className="input"
              value={last}
              onChange={(e) => setLast(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Preferred name</label>
            <input
              className="input"
              value={preferred}
              onChange={(e) => setPreferred(e.target.value)}
              placeholder="What they go by"
            />
          </div>
          <div className="field">
            <label>Date of birth</label>
            <input
              className="input"
              type="date"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Gender</label>
            <select
              className="select"
              value={gender}
              onChange={(e) => setGender(e.target.value)}
            >
              <option value="">—</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="non_binary">Non-binary</option>
              <option value="prefer_not_to_say">Prefer not to say</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="field">
            <label>Marital status</label>
            <select
              className="select"
              value={marital}
              onChange={(e) => setMarital(e.target.value)}
            >
              <option value="">—</option>
              <option value="single">Single</option>
              <option value="married">Married</option>
              <option value="partnered">Partnered</option>
              <option value="divorced">Divorced</option>
              <option value="widowed">Widowed</option>
            </select>
          </div>

          <SectionHeading>Contact</SectionHeading>
          <div className="field">
            <label>Work email</label>
            <input
              className="input"
              type="email"
              value={workEmail}
              onChange={(e) => setWorkEmail(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Personal email</label>
            <input
              className="input"
              type="email"
              value={personalEmail}
              onChange={(e) => setPersonalEmail(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Phone</label>
            <input
              className="input"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+27 71 234 5678"
            />
          </div>
          <div className="field">
            <label>Alternate phone</label>
            <input
              className="input"
              type="tel"
              value={altPhone}
              onChange={(e) => setAltPhone(e.target.value)}
            />
          </div>

          <SectionHeading>Address</SectionHeading>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Address line 1</label>
            <input
              className="input"
              value={addr1}
              onChange={(e) => setAddr1(e.target.value)}
            />
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Address line 2</label>
            <input
              className="input"
              value={addr2}
              onChange={(e) => setAddr2(e.target.value)}
            />
          </div>
          <div className="field">
            <label>City</label>
            <input
              className="input"
              value={city}
              onChange={(e) => setCity(e.target.value)}
            />
          </div>
          <div className="field">
            <label>State / province</label>
            <input
              className="input"
              value={state}
              onChange={(e) => setState(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Postal code</label>
            <input
              className="input"
              value={postal}
              onChange={(e) => setPostal(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Country</label>
            <input
              className="input"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              placeholder="ZA, GB, …"
            />
          </div>

          <SectionHeading>Employment</SectionHeading>
          <div className="field">
            <label>Job title</label>
            <select
              className="select"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            >
              <option value="">— Unassigned —</option>
              {(jobTitles.data ?? []).map((j) => (
                <option key={j.id} value={j.id}>
                  {j.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Department</label>
            <select
              className="select"
              value={dept}
              onChange={(e) => setDept(e.target.value)}
            >
              <option value="">— Unassigned —</option>
              {(departments.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Location</label>
            <select
              className="select"
              value={loc}
              onChange={(e) => setLoc(e.target.value)}
            >
              <option value="">— Unassigned —</option>
              {(locations.data ?? []).map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Employment type</label>
            <select
              className="select"
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option value="permanent">Permanent</option>
              <option value="contract">Contract</option>
              <option value="intern">Intern</option>
              <option value="consultant">Consultant</option>
              <option value="part_time">Part-time</option>
            </select>
          </div>
        </div>
      </form>
    </Modal>
  );
}

/* ---------------------------------------------------------------- *
 * Tabs
 * ---------------------------------------------------------------- */

function OverviewTab({ employee }: { employee: EmployeeDetail }) {
  const tenure = tenureSummary(employee.start_date);
  const hasPii = Boolean(employee.national_id || employee.passport_number);

  return (
    <div className="grid" style={{ gridTemplateColumns: "1.4fr 1fr", gap: 16, marginTop: 16 }}>
      <div className="col" style={{ gap: 16 }}>
        <Card>
          <CardHead title="At a glance" />
          <div
            className="card-body"
            style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}
          >
            <Mini
              label="Tenure"
              value={tenure}
              sub={employee.start_date ? `Since ${fmtDate(employee.start_date)}` : undefined}
            />
            <Mini
              label="Employment"
              value={statusLabel(employee.employment_type || "—")}
              sub={statusLabel(employee.employment_status || "")}
            />
            <Mini
              label="Manager"
              value={employee.line_manager_name || "—"}
              sub={employee.department_name}
            />
            <Mini
              label="Grade"
              value={employee.grade_name || "—"}
              sub={employee.position_name}
            />
            <Mini
              label="Location"
              value={employee.work_location_name || "—"}
              sub={employee.city || employee.country}
            />
            <Mini
              label="Cost centre"
              value={employee.cost_centre_name || "—"}
              sub={employee.confirmation_date ? `Confirmed ${fmtDate(employee.confirmation_date)}` : undefined}
            />
          </div>
        </Card>
      </div>

      <div className="col" style={{ gap: 16 }}>
        <Card>
          <CardHead title="Personal details" />
          <CardBody style={{ paddingTop: 4 }}>
            <KV label="Preferred name" value={employee.preferred_name || "—"} />
            <KV label="Gender" value={statusLabel(employee.gender || "—")} />
            <KV label="Date of birth" value={employee.date_of_birth ? fmtDate(employee.date_of_birth) : "—"} />
            <KV label="Marital status" value={statusLabel(employee.marital_status || "—")} />
            <KV label="National ID" value={employee.national_id || "—"} confidential={hasPii} />
            <KV label="Personal email" value={employee.personal_email || "—"} />
            <KV label="Phone" value={employee.phone || "—"} confidential />
            <KV
              label="Address"
              value={
                [employee.address_line1, employee.city, employee.country]
                  .filter(Boolean)
                  .join(", ") || "—"
              }
            />
          </CardBody>
        </Card>

        <Card>
          <CardHead title="Bank details" sub="Restricted · payroll only" />
          <CardBody style={{ paddingTop: 4 }}>
            <KV label="Bank" value={employee.bank_name || "—"} />
            <KV label="Account" value={employee.bank_account_number || "—"} confidential />
            <KV label="Branch / routing" value={employee.bank_branch_code || "—"} />
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function EmploymentTab({ employee }: { employee: EmployeeDetail }) {
  /* Pull the audit trail scoped to this employee and render the most
     recent ~10 events as a timeline. Falls back to a single "Joined"
     node when the audit log is empty. */
  const auditQ = useQuery({
    queryKey: ["audit", "employee", employee.id],
    queryFn: () =>
      listAuditLog({
        entity_type: "Employee",
        search: employee.id,
        page_size: 25,
      }),
  });

  const rows = (auditQ.data?.results ?? []).slice(0, 10);

  return (
    <div style={{ marginTop: 16 }}>
      <Card>
        <CardHead title="Employment timeline" sub="Promotions, transfers, and changes" />
        <CardBody>
          {auditQ.isLoading ? (
            <div style={{ padding: 20, color: "var(--text-3)" }}>Loading…</div>
          ) : rows.length === 0 ? (
            <div className="timeline">
              <div className="timeline-node done">
                <div className="who">Joined</div>
                <div className="when">
                  {employee.start_date ? fmtDate(employee.start_date) : "—"}
                </div>
                <div className="what">
                  {[employee.job_title_name, employee.department_name, employee.work_location_name]
                    .filter(Boolean)
                    .join(" · ")}
                </div>
              </div>
            </div>
          ) : (
            <div className="timeline">
              {rows.map((a) => (
                <div key={a.id} className="timeline-node done">
                  <div className="who">{a.action}</div>
                  <div className="when">
                    {fmtDate(a.created_at)} · {a.actor_name || "System"}
                  </div>
                  {a.description && <div className="what">{a.description}</div>}
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function LeaveTab({ employeeId }: { employeeId: string }) {
  const balancesQ = useQuery<LeaveBalance[]>({
    queryKey: ["leave-balances", employeeId],
    queryFn: async () => {
      /* listLeaveBalances doesn't take a filter today; we filter
         client-side until the API gains a param. */
      const all = await listLeaveBalances();
      return all.filter((b) => b.employee === employeeId);
    },
  });
  const requestsQ = useQuery({
    queryKey: ["leave-requests", employeeId],
    queryFn: () => listLeaveRequests({ employee: employeeId }),
  });

  const balances = balancesQ.data ?? [];
  const requests: LeaveRequest[] = requestsQ.data?.results ?? [];

  return (
    <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr", marginTop: 16, gap: 16 }}>
      {balancesQ.isLoading && (
        <Card>
          <div className="card-body" style={{ color: "var(--text-3)" }}>Loading balances…</div>
        </Card>
      )}
      {!balancesQ.isLoading && balances.length === 0 && (
        <Card style={{ gridColumn: "1 / -1" }}>
          <div className="empty" style={{ margin: 16 }}>
            <div className="title">No leave balances yet</div>
            <div className="lede">
              Balances appear once leave types are configured for this employee.
            </div>
          </div>
        </Card>
      )}
      {balances.slice(0, 3).map((b) => {
        const entitlement = Number(b.entitlement_days) || 0;
        const taken = Number(b.taken_days) || 0;
        const remaining = Number(b.balance_days) || entitlement - taken;
        return (
          <Card key={b.id}>
            <div style={{ padding: 18 }}>
              <div style={{ fontSize: 12, color: "var(--text-3)" }}>
                {b.leave_type_name || "Leave"}
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginTop: 4 }}>
                <span style={{ fontSize: 32, color: "var(--ink-3)" }}>{remaining}</span>
                <span style={{ color: "var(--text-3)", fontSize: 13 }}>
                  / {entitlement} days
                </span>
              </div>
              <div style={{ marginTop: 10 }}>
                <Meter value={taken} max={entitlement || 1} thin />
              </div>
            </div>
          </Card>
        );
      })}
      <Card style={{ gridColumn: "1 / -1" }}>
        <CardHead title="Leave history" />
        {requestsQ.isLoading ? (
          <div className="card-body" style={{ color: "var(--text-3)" }}>Loading…</div>
        ) : requests.length === 0 ? (
          <div className="empty" style={{ margin: 16 }}>
            <div className="title">No leave requests on file</div>
            <div className="lede">Requests created here appear once the employee applies for leave.</div>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Dates</th>
                <th>Days</th>
                <th>Status</th>
                <th>Submitted</th>
              </tr>
            </thead>
            <tbody>
              {requests.slice(0, 8).map((r) => (
                <tr key={r.id}>
                  <td>{r.leave_type_name || "—"}</td>
                  <td>
                    {fmtDate(r.start_date)} – {fmtDate(r.end_date)}
                  </td>
                  <td>{r.days_requested}</td>
                  <td>
                    <StatusBadge status={r.status_display || statusLabel(r.status)} />
                  </td>
                  <td className="muted">{r.submitted_at ? fmtDate(r.submitted_at) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

function DocsTab({ employeeId }: { employeeId: string }) {
  const docsQ = useQuery({
    queryKey: ["documents", employeeId],
    queryFn: () => listDocuments({ employee: employeeId, page_size: 50 }),
  });
  const docs = docsQ.data?.results ?? [];

  return (
    <Card style={{ marginTop: 16 }}>
      <CardHead
        title="Documents"
        sub={docsQ.isLoading ? "Loading…" : `${docs.length} on file`}
      />
      {!docsQ.isLoading && docs.length === 0 ? (
        <div className="empty" style={{ margin: 16 }}>
          <div className="title">No documents yet</div>
          <div className="lede">Uploads will appear here once HR or the employee adds them.</div>
        </div>
      ) : (
        <div
          className="card-body"
          style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8 }}
        >
          {docs.map((d) => (
            <FileRow
              key={d.id}
              name={d.title}
              sub={`${d.category_name || "Document"} · ${fmtDate(d.created_at)}`}
              size={d.current_version?.file_size}
              action={<StatusBadge status={d.status_display || statusLabel(d.status)} />}
            />
          ))}
        </div>
      )}
    </Card>
  );
}

function CompTab({ employee }: { employee: EmployeeDetail }) {
  /* Salary is RBAC-gated server-side: viewers without `payroll.view_salary`
     receive `***` from the masking layer, so we render whatever the backend
     allows. */
  const salaryDisplay =
    employee.current_salary && employee.current_salary !== "***"
      ? `${employee.salary_currency || ""} ${employee.current_salary}`.trim()
      : employee.current_salary === "***"
        ? "Restricted"
        : "—";

  return (
    <Card style={{ marginTop: 16 }}>
      <CardHead
        title="Compensation"
        sub={
          employee.current_salary === "***"
            ? "You don't have access to salary figures"
            : "Restricted view"
        }
      />
      <div
        className="card-body"
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}
      >
        <div>
          <div style={{ fontSize: 42, color: "var(--ink-3)" }}>{salaryDisplay}</div>
          <div style={{ color: "var(--text-3)" }}>
            {[employee.department_name, employee.grade_name].filter(Boolean).join(" · ") || "—"}
          </div>
          <div className="divider" />
          <KV label="Pay frequency" value="Monthly" />
          <KV label="Currency" value={employee.salary_currency || "—"} />
          <KV label="Position" value={employee.position_name || "—"} />
          <KV label="Cost centre" value={employee.cost_centre_name || "—"} />
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Contracts on file</div>
          {(employee.contracts ?? []).length === 0 ? (
            <div style={{ fontSize: 12, color: "var(--text-3)" }}>
              No contracts yet — create one from the <strong>Contracts</strong> tab.
            </div>
          ) : (
            (employee.contracts ?? []).slice(0, 5).map((c) => (
              <div
                key={c.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "10px 0",
                  borderBottom: "1px solid var(--hairline-2)",
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>
                    {c.base_salary ? `${c.currency || ""} ${c.base_salary}` : "—"}
                  </div>
                  <div style={{ fontSize: 11.5, color: "var(--text-3)" }}>
                    {statusLabel(c.contract_type)}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 12, color: "var(--text-3)" }}>
                    {fmtDate(c.start_date)}
                  </div>
                  <div style={{ fontSize: 11.5, color: "var(--text-4)" }}>
                    {c.status || "draft"}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </Card>
  );
}

function PerfTab({ employeeId }: { employeeId: string }) {
  const reviewsQ = useQuery({
    queryKey: ["performance-reviews", employeeId],
    queryFn: () => listPerformanceReviews({ employee: employeeId, page: 1 }),
  });
  const reviews = reviewsQ.data?.results ?? [];

  const latestRating = useMemo(() => {
    const completed = reviews.filter((r) => r.status === "completed" && r.overall_rating);
    if (completed.length === 0) return null;
    return Number(completed[0].overall_rating);
  }, [reviews]);

  return (
    <div style={{ marginTop: 16 }}>
      <Card>
        <CardHead
          title="Review cycles"
          sub={
            latestRating != null
              ? `Latest rating ${latestRating.toFixed(1)} / 5`
              : "No completed reviews yet"
          }
        />
        <CardBody>
          {reviewsQ.isLoading ? (
            <div style={{ padding: 20, color: "var(--text-3)" }}>Loading…</div>
          ) : reviews.length === 0 ? (
            <Empty
              icon="chart"
              title="No reviews yet"
              lede="Start a review from the Performance page once a cycle is open."
            />
          ) : (
            reviews.map((r, i) => (
              <div
                key={r.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 0",
                  borderBottom: i === reviews.length - 1 ? "none" : "1px solid var(--hairline-2)",
                }}
              >
                <div>
                  <div style={{ fontWeight: 500, fontSize: 13.5 }}>
                    {r.cycle_name || "Cycle"}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-3)" }}>
                    {r.due_date ? `Due ${fmtDate(r.due_date)}` : ""}
                  </div>
                </div>
                <Stars value={r.overall_rating ? Number(r.overall_rating) : null} />
                <StatusBadge status={r.status_display || statusLabel(r.status)} />
              </div>
            ))
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function TrainingTab({ employeeId }: { employeeId: string }) {
  const trainingQ = useQuery({
    queryKey: ["training-records", employeeId],
    queryFn: () => listTrainingRecords({ employee: employeeId }),
  });
  const records = trainingQ.data?.results ?? [];

  return (
    <Card style={{ marginTop: 16 }}>
      <CardHead title="Training & certifications" />
      {trainingQ.isLoading ? (
        <div className="card-body" style={{ color: "var(--text-3)" }}>Loading…</div>
      ) : records.length === 0 ? (
        <Empty
          icon="award"
          title="No training records"
          lede="Course completions show here as the employee finishes them."
        />
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Course</th>
              <th>Enrolled</th>
              <th>Completed</th>
              <th>Score</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {records.map((c) => (
              <tr key={c.id}>
                <td>{c.course_title || "—"}</td>
                <td className="muted">{c.enrolled_at ? fmtDate(c.enrolled_at) : "—"}</td>
                <td className="muted">{c.completed_at ? fmtDate(c.completed_at) : "—"}</td>
                <td className="num">{c.score ?? "—"}</td>
                <td>
                  <StatusBadge status={statusLabel(c.status || "")} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

function HistoryTab({ employee }: { employee: EmployeeDetail }) {
  const auditQ = useQuery({
    queryKey: ["audit", "employee-history", employee.id],
    queryFn: () =>
      listAuditLog({
        entity_type: "Employee",
        search: employee.id,
        page_size: 50,
      }),
  });
  const rows = auditQ.data?.results ?? [];

  return (
    <Card style={{ marginTop: 16 }}>
      <CardHead title="Change history" sub="Audit log scoped to this employee" />
      {auditQ.isLoading ? (
        <div className="card-body" style={{ color: "var(--text-3)" }}>Loading…</div>
      ) : rows.length === 0 ? (
        <Empty
          icon="history"
          title="No history yet"
          lede="Every change to this record appears here once HR makes one."
        />
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>When</th>
              <th>Who</th>
              <th>Action</th>
              <th>Entity</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id}>
                <td className="muted num">{fmtDate(a.created_at)}</td>
                <td>{a.actor_name || "System"}</td>
                <td>{a.action}</td>
                <td className="muted">{a.entity_type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
