import { create } from "zustand";
import { persist } from "zustand/middleware";

import * as Demo from "./demo";
import { nowIso, todayShort, uid } from "./export";

/* =============================================================
 * Bunchly runtime store.
 *
 * Every collection on the prototype's demo data is mirrored here as
 * mutable runtime state. Actions on every page (add, approve, reject,
 * tick, schedule, register, upload, etc.) call into this store so the
 * UI updates immediately and the state survives a page reload via
 * localStorage. When real backend endpoints land, the corresponding
 * action body is the place to add the HTTP call.
 * ============================================================= */

/* ---------- Types ---------- */

export type LeaveRequest = (typeof Demo.LEAVE_REQUESTS)[number];
export type DocumentRecord = (typeof Demo.DOCUMENTS)[number] & { fileSizeBytes?: number };
export type Candidate = (typeof Demo.CANDIDATES)[number];
export type JobReq = (typeof Demo.JOB_REQS)[number];
export type Policy = (typeof Demo.POLICIES)[number];
export type HRCase = (typeof Demo.HR_CASES)[number] & { thread?: ThreadMessage[] };
export type Asset = (typeof Demo.ASSETS)[number];
export type Course = (typeof Demo.COURSES)[number];
export type EduClaim = (typeof Demo.EDU_CLAIMS)[number];
export type PayrollPeriod = (typeof Demo.PAYROLL_PERIODS)[number];
export type AuditLog = (typeof Demo.AUDIT_LOGS)[number];
export interface AttendanceRow {
  who: string;
  av: string;
  in: string | null;
  out: string | null;
  status: string;
  hours: string;
}
export type Employee = (typeof Demo.EMPLOYEES)[number];
export type PerformanceReview = (typeof Demo.PERFORMANCE_REVIEWS)[number];
export type OnboardingProgramme = (typeof Demo.ONBOARDING_PROGRAMMES)[number];

export interface ThreadMessage {
  id: string;
  author: string;
  av: string;
  body: string;
  when: string;
  internal?: boolean;
}

export interface OnboardingTaskRecord {
  id: string;
  programmeId: string;
  phase: string;
  task: string;
  done: boolean;
  owner: string;
  createdAt: string;
}

export interface InterviewRecord {
  id: string;
  candidateId: string;
  who: string;
  role: string;
  when: string;
  score: number | null;
}

export interface ImportBatch {
  id: string;
  type: string;
  by: string;
  rows: string;
  status: string;
  when: string;
}

export interface SavedReport {
  id: string;
  name: string;
  group: string;
  createdAt: string;
  favourite: boolean;
}

export interface CourseAssignment {
  id: string;
  courseId: string;
  employeeName: string;
  status: "Assigned" | "In progress" | "Complete";
  assignedAt: string;
}

export interface BenefitRule {
  eligibility: string;
  approval: string;
  documents: string;
  waitDays: number;
}

export type BenefitType = (typeof Demo.BENEFIT_TYPES)[number] & { rules?: BenefitRule };

export interface BenefitEnrolment {
  id: string;
  benefitId: string;
  employee: string;
  plan: string;
  enrolledAt: string;
}

export interface WorkspaceSettings {
  orgName: string;
  tradingName: string;
  primaryDomain: string;
  country: string;
  currency: string;
  workingHours: string;
}

export interface EmailSettings {
  fromName: string;
  fromEmail: string;
  replyTo: string;
  provider: "Resend" | "SMTP";
  apiKeyMasked: string;
  smtpHost: string;
  smtpPort: number;
}

export interface NotificationTrigger {
  id: string;
  name: string;
  on: boolean;
  channels: string[];
}

export interface SecuritySettings {
  require2fa: boolean;
  ssoGoogle: boolean;
  ssoSaml: boolean;
  trustDeviceDays: number;
  sessionTimeoutHours: number;
  lockIpRanges: boolean;
  autoRevokeOnExit: boolean;
}

export interface IntegrationRecord {
  name: string;
  desc: string;
  logo: string;
  on: boolean;
}

export interface BunchlyState {
  /* core collections */
  employees: Employee[];
  leaveRequests: LeaveRequest[];
  documents: DocumentRecord[];
  candidates: Candidate[];
  jobReqs: JobReq[];
  onboardingProgrammes: OnboardingProgramme[];
  onboardingTasks: OnboardingTaskRecord[];
  policies: Policy[];
  policyAcknowledgements: Array<{ policyId: string; employee: string; ackedAt: string }>;
  hrCases: HRCase[];
  assets: Asset[];
  courses: Course[];
  courseAssignments: CourseAssignment[];
  benefitTypes: BenefitType[];
  benefitEnrolments: BenefitEnrolment[];

  /* settings */
  workspaceSettings: WorkspaceSettings;
  emailSettings: EmailSettings;
  notificationTriggers: NotificationTrigger[];
  securitySettings: SecuritySettings;
  integrations: IntegrationRecord[];
  educationClaims: EduClaim[];
  payrollPeriods: PayrollPeriod[];
  performanceReviews: PerformanceReview[];
  auditLogs: AuditLog[];
  attendanceToday: AttendanceRow[];
  interviews: InterviewRecord[];
  importBatches: ImportBatch[];
  savedReports: SavedReport[];

  /* clock */
  clock: { who: string; clockedInAt: string | null };

  /* ---------- Employees ---------- */
  addEmployee: (p: {
    firstName: string;
    lastName: string;
    email: string;
    dept: string;
    title: string;
    manager: string;
    type: string;
    startDate: string;
  }) => Employee;
  updateEmployee: (
    id: string,
    patch: Partial<Pick<Employee, "name" | "title" | "dept" | "manager" | "email" | "location" | "type">>,
  ) => void;

  /* ---------- Leave ---------- */
  submitLeave: (p: {
    employee: string;
    av: string;
    type: string;
    start: string;
    end: string;
    days: number;
    reason: string;
    manager: string;
  }) => LeaveRequest;
  approveLeave: (id: string, decidedBy: string) => void;
  rejectLeave: (id: string, decidedBy: string, reason?: string) => void;

  /* ---------- Documents ---------- */
  uploadDocument: (p: {
    name: string;
    category: string;
    owner: string;
    sizeKb: number;
    confidential: boolean;
  }) => DocumentRecord;
  verifyDocument: (id: string, verifier: string) => void;

  /* ---------- Education claims ---------- */
  submitClaim: (p: {
    employee: string;
    av: string;
    child: string;
    level: string;
    institution: string;
    period: string;
    amount: number;
  }) => EduClaim;
  approveClaim: (id: string, by: string) => void;
  rejectClaim: (id: string, by: string) => void;
  markClaimPaid: (id: string, by: string) => void;

  /* ---------- Recruitment ---------- */
  createRequisition: (p: {
    title: string;
    dept: string;
    location: string;
    openings: number;
    manager: string;
  }) => JobReq;
  publishRequisition: (id: string) => void;
  addCandidate: (p: { name: string; role: string; source: string; location: string; expected: string }) => Candidate;
  moveCandidateStage: (id: string, stage: string) => void;
  scheduleInterview: (p: {
    candidateId: string;
    who: string;
    role: string;
    when: string;
  }) => InterviewRecord;

  /* ---------- Onboarding ---------- */
  createProgramme: (p: {
    name: string;
    startedAt: string;
    manager: string;
    av: string;
    tasksTotal: number;
  }) => OnboardingProgramme;
  addOnboardingTask: (p: { programmeId: string; phase: string; task: string; owner: string }) => OnboardingTaskRecord;
  toggleOnboardingTask: (id: string) => void;

  /* ---------- Policies ---------- */
  addPolicy: (p: { title: string; version: string; category: string; mandatory: boolean }) => Policy;
  remindUnacknowledged: (policyId: string) => number; // returns reminder count
  acknowledgePolicy: (policyId: string, employee: string) => void;

  /* ---------- HR Cases ---------- */
  raiseCase: (p: { subject: string; category: string; priority: string; raisedBy: string; av: string; body: string }) => HRCase;
  addCaseReply: (caseId: string, author: string, av: string, body: string, internal?: boolean) => void;
  setCaseStatus: (caseId: string, status: string) => void;
  assignCase: (caseId: string, assignee: string) => void;

  /* ---------- Assets ---------- */
  registerAsset: (p: {
    name: string;
    category: string;
    serial: string;
    condition: string;
  }) => Asset;
  assignAsset: (id: string, to: string, av: string) => void;
  returnAsset: (id: string) => void;

  /* ---------- Courses ---------- */
  addCourse: (p: { title: string; category: string; duration: string; mandatory: boolean; due: string | null }) => Course;
  markCourseComplete: (courseId: string, employee: string) => void;
  bumpCourseProgress: (courseId: string, delta: number) => void;

  /* ---------- Settings ---------- */
  updateWorkspaceSettings: (patch: Partial<WorkspaceSettings>) => void;
  updateEmailSettings: (patch: Partial<EmailSettings>) => void;
  sendTestEmail: (to?: string) => void;
  toggleNotificationTrigger: (id: string) => void;
  updateSecuritySettings: (patch: Partial<SecuritySettings>) => void;
  toggleIntegration: (name: string) => void;

  /* ---------- Benefits ---------- */
  addBenefit: (p: {
    name: string;
    provider: string;
    cost: string;
    waitDays: number;
    rule?: BenefitRule;
  }) => BenefitType;
  updateBenefitRule: (id: string, rule: BenefitRule) => void;
  enrolBenefit: (p: { benefitId: string; employee: string; plan: string }) => BenefitEnrolment | null;
  unenrolBenefit: (enrolmentId: string) => void;

  /* ---------- Imports ---------- */
  runImport: (p: { type: string; by: string; rows: number; status?: string }) => ImportBatch;

  /* ---------- Reports ---------- */
  saveReport: (p: { name: string; group: string }) => SavedReport;
  toggleFavouriteReport: (id: string) => void;

  /* ---------- Payroll ---------- */
  startPayrollRun: (period: string) => PayrollPeriod;
  approvePayrollRun: (id: string) => void;

  /* ---------- Attendance ---------- */
  clockIn: (who: string) => void;
  clockOut: () => void;
  addAttendanceManualEntry: (p: { who: string; av: string; in: string | null; out: string | null; status: string; hours: string }) => AttendanceRow;

  /* ---------- Performance ---------- */
  startReview: (p: { who: string; av: string; cycle: string; manager: string; due: string }) => PerformanceReview;
  setReviewRating: (id: string, rating: number) => void;
  setReviewStatus: (id: string, status: string) => void;

  /* ---------- Audit ---------- */
  logAction: (actor: string, action: string, entity: string) => void;

  /* ---------- Reset ---------- */
  resetAll: () => void;
}

/* ---------- helpers ---------- */
function nowAuditTime() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const initialSeed = () => ({
  employees: [...Demo.EMPLOYEES],
  leaveRequests: [...Demo.LEAVE_REQUESTS],
  documents: [...Demo.DOCUMENTS],
  candidates: [...Demo.CANDIDATES],
  jobReqs: [...Demo.JOB_REQS],
  onboardingProgrammes: [...Demo.ONBOARDING_PROGRAMMES],
  onboardingTasks: Demo.ONBOARDING_PROGRAMMES.flatMap((p) =>
    Demo.ONBOARDING_TASKS_TPL.flatMap((phase) =>
      phase.tasks.map((t, ti) => ({
        id: uid("T-"),
        programmeId: p.id,
        phase: phase.phase,
        task: t,
        done: false, // initial state; we set "done" using counts below
        owner: ["HR Team", "Manager", "IT", "Employee"][ti % 4],
        createdAt: nowIso(),
      })),
    ),
  ).map((t, idx, all) => {
    // mark the first `tasksDone` per programme as done, matching the prototype
    const programme = Demo.ONBOARDING_PROGRAMMES.find((p) => p.id === t.programmeId);
    if (!programme) return t;
    const tasksForProgramme = all.filter((x) => x.programmeId === t.programmeId);
    const positionWithinProgramme = tasksForProgramme.indexOf(t);
    return { ...t, done: positionWithinProgramme < programme.tasksDone };
  }),
  policies: [...Demo.POLICIES],
  policyAcknowledgements: [] as Array<{ policyId: string; employee: string; ackedAt: string }>,
  hrCases: Demo.HR_CASES.map<HRCase>((c) => ({ ...c, thread: [] })),
  assets: [...Demo.ASSETS],
  courses: [...Demo.COURSES],
  courseAssignments: [] as CourseAssignment[],
  benefitTypes: Demo.BENEFIT_TYPES.map((b) => ({
    ...b,
    rules: {
      eligibility: `All FT after ${b.waitDays} days`,
      approval: "HR → Finance",
      documents: "Invoice + ID",
      waitDays: b.waitDays,
    } as BenefitRule,
  })) as BenefitType[],
  benefitEnrolments: [] as BenefitEnrolment[],

  workspaceSettings: {
    orgName: "Acme Holdings Pty Ltd",
    tradingName: "Acme",
    primaryDomain: "acme.bunchly.com",
    country: "South Africa",
    currency: "USD",
    workingHours: "09:00 – 17:30",
  } as WorkspaceSettings,
  emailSettings: {
    fromName: "Acme People · via Bunchly",
    fromEmail: "people@acme.bunchly.io",
    replyTo: "hr@acme.com",
    provider: "Resend",
    apiKeyMasked: "re_••••••••••••",
    smtpHost: "smtp.bunchly.io",
    smtpPort: 587,
  } as EmailSettings,
  notificationTriggers: [
    { id: "nt-birthday", name: "Employee birthday", on: true, channels: ["Email", "In-app", "Slack"] },
    { id: "nt-contract", name: "Contract expiring (90/60/30 days)", on: true, channels: ["Email", "In-app"] },
    { id: "nt-probation", name: "Probation ending", on: true, channels: ["Email", "In-app"] },
    { id: "nt-leave-approval", name: "Leave approval needed", on: true, channels: ["Email", "In-app", "Slack"] },
    { id: "nt-edu-claim", name: "Education claim status change", on: true, channels: ["Email"] },
    { id: "nt-missing-doc", name: "Missing document reminder", on: false, channels: ["Email"] },
    { id: "nt-policy", name: "Policy not acknowledged", on: true, channels: ["Email", "In-app"] },
    { id: "nt-holiday", name: "Public holiday this week", on: false, channels: ["In-app"] },
  ] as NotificationTrigger[],
  securitySettings: {
    require2fa: true,
    ssoGoogle: true,
    ssoSaml: false,
    trustDeviceDays: 30,
    sessionTimeoutHours: 4,
    lockIpRanges: true,
    autoRevokeOnExit: true,
  } as SecuritySettings,
  integrations: [
    { name: "Slack", desc: "Notify channels, DM approvers", logo: "💬", on: true },
    { name: "Google Workspace", desc: "SSO, calendars, drive", logo: "G", on: true },
    { name: "Microsoft 365", desc: "SSO, Teams, OneDrive", logo: "M", on: false },
    { name: "Xero", desc: "Payroll & GL export", logo: "X", on: true },
    { name: "Stripe", desc: "Contractor payouts", logo: "S", on: false },
    { name: "BambooHR", desc: "Migration import only", logo: "B", on: false },
    { name: "Resend", desc: "Transactional email", logo: "R", on: true },
    { name: "Zapier", desc: "1,000+ tools", logo: "Z", on: false },
    { name: "DocuSign", desc: "Contract signing", logo: "D", on: false },
  ] as IntegrationRecord[],
  educationClaims: [...Demo.EDU_CLAIMS],
  payrollPeriods: [...Demo.PAYROLL_PERIODS],
  performanceReviews: [...Demo.PERFORMANCE_REVIEWS],
  auditLogs: [...Demo.AUDIT_LOGS],
  attendanceToday: [...Demo.ATTENDANCE_TODAY],
  interviews: [] as InterviewRecord[],
  importBatches: [
    {
      id: "IM-2026-01",
      type: "Employees",
      by: "Olamide Diallo",
      rows: "12 of 12",
      status: "Complete",
      when: "14 May 2026 · 10:42",
    },
    {
      id: "IM-2026-02",
      type: "Documents",
      by: "Pia Lindberg",
      rows: "84 of 84",
      status: "Complete",
      when: "18 Mar 2026 · 14:11",
    },
    {
      id: "IM-2026-03",
      type: "Leave balances",
      by: "Olamide Diallo",
      rows: "120 of 124",
      status: "Pending",
      when: "2 Jan 2026 · 09:21",
    },
  ] as ImportBatch[],
  savedReports: [] as SavedReport[],
  clock: { who: "Esi Asante", clockedInAt: new Date().toISOString() } as { who: string; clockedInAt: string | null },
});

export const useStore = create<BunchlyState>()(
  persist(
    (set, get) => ({
      ...initialSeed(),

      /* ---------- Employees ---------- */
      addEmployee: (p) => {
        const id = `E-${Math.floor(Math.random() * 9000 + 1000)}`;
        const rec: Employee = {
          id,
          name: `${p.firstName} ${p.lastName}`,
          title: p.title,
          dept: p.dept,
          location: "Cape Town",
          status: "Active",
          type: p.type,
          joined: p.startDate,
          manager: p.manager,
          av: `av-${(get().employees.length % 8) + 1}`,
          initials: `${p.firstName[0] || ""}${p.lastName[0] || ""}`.toUpperCase(),
          probation: true,
          contractEnd: null,
          leaveBalance: 21,
          email: p.email,
        };
        set((s) => ({ employees: [rec, ...s.employees] }));
        get().logAction(p.firstName, "Created employee", id);
        return rec;
      },

      updateEmployee: (id, patch) => {
        set((s) => ({
          employees: s.employees.map((e) =>
            e.id === id ? { ...e, ...patch } : e,
          ),
        }));
        get().logAction("System", "Updated employee", id);
      },

      /* ---------- Leave ---------- */
      submitLeave: (p) => {
        const id = uid("LR-");
        const rec: LeaveRequest = {
          id,
          who: p.employee,
          av: p.av,
          type: p.type,
          start: p.start,
          end: p.end,
          days: p.days,
          status: "Pending Approval",
          stage: "Manager",
          manager: p.manager,
          reason: p.reason,
          submittedAt: new Date().toISOString().slice(0, 10),
        };
        set((s) => ({ leaveRequests: [rec, ...s.leaveRequests] }));
        get().logAction(p.employee, "Submitted leave request", id);
        return rec;
      },
      approveLeave: (id, by) => {
        set((s) => ({
          leaveRequests: s.leaveRequests.map((r) =>
            r.id === id ? { ...r, status: "Approved", stage: "Done" } : r,
          ),
        }));
        get().logAction(by, "Approved leave request", id);
      },
      rejectLeave: (id, by) => {
        set((s) => ({
          leaveRequests: s.leaveRequests.map((r) =>
            r.id === id ? { ...r, status: "Rejected", stage: "Done" } : r,
          ),
        }));
        get().logAction(by, "Rejected leave request", id);
      },

      /* ---------- Documents ---------- */
      uploadDocument: (p) => {
        const id = `DOC-${Math.floor(Math.random() * 9000 + 1000)}`;
        const rec: DocumentRecord = {
          id,
          name: p.name,
          category: p.category,
          owner: p.owner,
          uploaded: new Date().toISOString().slice(0, 10),
          size: p.sizeKb > 1024 ? `${(p.sizeKb / 1024).toFixed(1)} MB` : `${p.sizeKb} KB`,
          status: "Pending Review",
          confidential: p.confidential,
          fileSizeBytes: p.sizeKb * 1024,
        };
        set((s) => ({ documents: [rec, ...s.documents] }));
        get().logAction(p.owner, "Uploaded document", id);
        return rec;
      },
      verifyDocument: (id, verifier) => {
        set((s) => ({
          documents: s.documents.map((d) => (d.id === id ? { ...d, status: "Verified" } : d)),
        }));
        get().logAction(verifier, "Verified document", id);
      },

      /* ---------- Education claims ---------- */
      submitClaim: (p) => {
        const id = `EC-${Math.floor(Math.random() * 9000 + 1000)}`;
        const rec: EduClaim = {
          id,
          employee: p.employee,
          av: p.av,
          child: p.child,
          level: p.level,
          institution: p.institution,
          period: p.period,
          amount: p.amount,
          status: "Pending HR",
          submitted: new Date().toISOString().slice(0, 10),
          stage: "HR Review",
        };
        set((s) => ({ educationClaims: [rec, ...s.educationClaims] }));
        get().logAction(p.employee, "Submitted education claim", id);
        return rec;
      },
      approveClaim: (id, by) => {
        set((s) => ({
          educationClaims: s.educationClaims.map((c) =>
            c.id === id ? { ...c, status: "Pending Payment", stage: "Accounts" } : c,
          ),
        }));
        get().logAction(by, "Approved education claim", id);
      },
      rejectClaim: (id, by) => {
        set((s) => ({
          educationClaims: s.educationClaims.map((c) =>
            c.id === id ? { ...c, status: "Rejected", stage: "Done" } : c,
          ),
        }));
        get().logAction(by, "Rejected education claim", id);
      },
      markClaimPaid: (id, by) => {
        set((s) => ({
          educationClaims: s.educationClaims.map((c) =>
            c.id === id ? { ...c, status: "Paid", stage: "Done" } : c,
          ),
        }));
        get().logAction(by, "Marked education claim paid", id);
      },

      /* ---------- Recruitment ---------- */
      createRequisition: (p) => {
        const id = `JR-${Math.floor(Math.random() * 900 + 100)}`;
        const rec: JobReq = {
          id,
          title: p.title,
          dept: p.dept,
          location: p.location,
          openings: p.openings,
          applicants: 0,
          status: "Draft",
          posted: null,
          manager: p.manager,
        };
        set((s) => ({ jobReqs: [rec, ...s.jobReqs] }));
        get().logAction(p.manager, "Created job requisition", id);
        return rec;
      },
      publishRequisition: (id) => {
        const today = new Date().toISOString().slice(0, 10);
        set((s) => ({
          jobReqs: s.jobReqs.map((r) => (r.id === id ? { ...r, status: "Open", posted: today } : r)),
        }));
        get().logAction("System", "Published job posting", id);
      },
      addCandidate: (p) => {
        const id = `C-${Math.floor(Math.random() * 9000 + 1000)}`;
        const rec: Candidate = {
          id,
          name: p.name,
          role: p.role,
          stage: "Applied",
          source: p.source,
          days: 0,
          rating: null,
          av: `av-${(get().candidates.length % 8) + 1}`,
          expected: p.expected,
          location: p.location,
        };
        set((s) => ({ candidates: [rec, ...s.candidates] }));
        // Also bump applicants on the matching job req if any.
        set((s) => ({
          jobReqs: s.jobReqs.map((r) =>
            r.title === p.role ? { ...r, applicants: r.applicants + 1 } : r,
          ),
        }));
        get().logAction(p.name, "Applied to role", id);
        return rec;
      },
      moveCandidateStage: (id, stage) => {
        set((s) => ({
          candidates: s.candidates.map((c) => (c.id === id ? { ...c, stage } : c)),
        }));
        get().logAction("Recruiter", `Moved candidate to ${stage}`, id);
      },
      scheduleInterview: (p) => {
        const rec: InterviewRecord = {
          id: uid("IV-"),
          candidateId: p.candidateId,
          who: p.who,
          role: p.role,
          when: p.when,
          score: null,
        };
        set((s) => ({ interviews: [rec, ...s.interviews] }));
        get().logAction(p.who, "Scheduled interview", rec.id);
        return rec;
      },

      /* ---------- Onboarding ---------- */
      createProgramme: (p) => {
        const id = `OB-${new Date().getFullYear()}-${String(get().onboardingProgrammes.length + 1).padStart(2, "0")}`;
        const rec: OnboardingProgramme = {
          id,
          name: p.name,
          startedAt: p.startedAt,
          progress: 0,
          tasksDone: 0,
          tasksTotal: p.tasksTotal,
          manager: p.manager,
          av: p.av,
        };
        set((s) => ({ onboardingProgrammes: [rec, ...s.onboardingProgrammes] }));
        get().logAction(p.manager, "Created onboarding programme", id);
        return rec;
      },
      addOnboardingTask: (p) => {
        const rec: OnboardingTaskRecord = {
          id: uid("T-"),
          programmeId: p.programmeId,
          phase: p.phase,
          task: p.task,
          done: false,
          owner: p.owner,
          createdAt: nowIso(),
        };
        set((s) => ({
          onboardingTasks: [...s.onboardingTasks, rec],
          onboardingProgrammes: s.onboardingProgrammes.map((prog) =>
            prog.id === p.programmeId ? { ...prog, tasksTotal: prog.tasksTotal + 1 } : prog,
          ),
        }));
        return rec;
      },
      toggleOnboardingTask: (id) => {
        const task = get().onboardingTasks.find((t) => t.id === id);
        if (!task) return;
        const willBeDone = !task.done;
        set((s) => ({
          onboardingTasks: s.onboardingTasks.map((t) => (t.id === id ? { ...t, done: willBeDone } : t)),
        }));
        // recompute progress on the programme
        const tasks = get().onboardingTasks.filter((t) => t.programmeId === task.programmeId);
        const done = tasks.filter((t) => t.done).length;
        const total = tasks.length;
        const progress = total === 0 ? 0 : Math.round((done / total) * 100);
        set((s) => ({
          onboardingProgrammes: s.onboardingProgrammes.map((p) =>
            p.id === task.programmeId
              ? { ...p, tasksDone: done, tasksTotal: total, progress }
              : p,
          ),
        }));
      },

      /* ---------- Policies ---------- */
      addPolicy: (p) => {
        const id = `POL-${String(get().policies.length + 1).padStart(3, "0")}`;
        const rec: Policy = {
          id,
          title: p.title,
          version: p.version,
          effective: new Date().toISOString().slice(0, 10),
          category: p.category,
          acknowledged: 0,
          total: get().employees.length,
          mandatory: p.mandatory,
        };
        set((s) => ({ policies: [rec, ...s.policies] }));
        get().logAction("Admin", "Created policy", id);
        return rec;
      },
      remindUnacknowledged: (policyId) => {
        const policy = get().policies.find((p) => p.id === policyId);
        if (!policy) return 0;
        const outstanding = policy.total - policy.acknowledged;
        get().logAction("System", `Sent acknowledgement reminder for ${policy.title}`, policyId);
        return outstanding;
      },
      acknowledgePolicy: (policyId, employee) => {
        if (
          get().policyAcknowledgements.some(
            (a) => a.policyId === policyId && a.employee === employee,
          )
        ) {
          return;
        }
        set((s) => ({
          policyAcknowledgements: [
            ...s.policyAcknowledgements,
            { policyId, employee, ackedAt: nowIso() },
          ],
          policies: s.policies.map((p) =>
            p.id === policyId ? { ...p, acknowledged: Math.min(p.total, p.acknowledged + 1) } : p,
          ),
        }));
        get().logAction(employee, "Acknowledged policy", policyId);
      },

      /* ---------- HR Cases ---------- */
      raiseCase: (p) => {
        const id = `HC-${Math.floor(Math.random() * 9000 + 1000)}`;
        const rec: HRCase = {
          id,
          subject: p.subject,
          category: p.category,
          priority: p.priority,
          status: "Open",
          raisedBy: p.raisedBy,
          av: p.av,
          sla: "On track",
          updated: "just now",
          assignee: null,
          thread: [
            {
              id: uid("M-"),
              author: p.raisedBy,
              av: p.av,
              body: p.body,
              when: todayShort(),
            },
          ],
        };
        set((s) => ({ hrCases: [rec, ...s.hrCases] }));
        get().logAction(p.raisedBy, "Raised HR case", id);
        return rec;
      },
      addCaseReply: (caseId, author, av, body, internal) => {
        const msg: ThreadMessage = {
          id: uid("M-"),
          author,
          av,
          body,
          when: todayShort(),
          internal,
        };
        set((s) => ({
          hrCases: s.hrCases.map((c) =>
            c.id === caseId
              ? {
                  ...c,
                  thread: [...(c.thread || []), msg],
                  updated: "just now",
                  status: c.status === "Open" ? "In Progress" : c.status,
                }
              : c,
          ),
        }));
        get().logAction(author, `Replied on case`, caseId);
      },
      setCaseStatus: (caseId, status) => {
        set((s) => ({
          hrCases: s.hrCases.map((c) =>
            c.id === caseId
              ? { ...c, status, updated: "just now", sla: status === "Resolved" ? "Met" : c.sla }
              : c,
          ),
        }));
        get().logAction("HR", `Set case status to ${status}`, caseId);
      },
      assignCase: (caseId, assignee) => {
        set((s) => ({
          hrCases: s.hrCases.map((c) => (c.id === caseId ? { ...c, assignee } : c)),
        }));
        get().logAction(assignee, "Took ownership of case", caseId);
      },

      /* ---------- Assets ---------- */
      registerAsset: (p) => {
        const id = `AST-${String(get().assets.length + 421).padStart(4, "0")}`;
        const rec: Asset = {
          id,
          name: p.name,
          category: p.category,
          serial: p.serial,
          assignedTo: null,
          av: null,
          condition: p.condition,
          since: null,
        };
        set((s) => ({ assets: [rec, ...s.assets] }));
        get().logAction("Admin", "Registered asset", id);
        return rec;
      },
      assignAsset: (id, to, av) => {
        const today = new Date().toISOString().slice(0, 10);
        set((s) => ({
          assets: s.assets.map((a) =>
            a.id === id ? { ...a, assignedTo: to, av, since: today } : a,
          ),
        }));
        get().logAction("IT", `Assigned asset to ${to}`, id);
      },
      returnAsset: (id) => {
        set((s) => ({
          assets: s.assets.map((a) =>
            a.id === id ? { ...a, assignedTo: null, av: null, since: null } : a,
          ),
        }));
        get().logAction("IT", "Asset returned", id);
      },

      /* ---------- Courses ---------- */
      addCourse: (p) => {
        const id = `L-${Math.floor(Math.random() * 9000 + 1000)}`;
        const headcount = get().employees.length;
        const rec: Course = {
          id,
          title: p.title,
          category: p.category,
          duration: p.duration,
          enrolled: p.mandatory ? headcount : 0,
          complete: 0,
          mandatory: p.mandatory,
          due: p.due,
        };
        set((s) => ({ courses: [rec, ...s.courses] }));
        get().logAction("Admin", "Added course", id);
        return rec;
      },
      markCourseComplete: (courseId, employee) => {
        if (
          get().courseAssignments.some(
            (a) => a.courseId === courseId && a.employeeName === employee && a.status === "Complete",
          )
        ) {
          return;
        }
        const a: CourseAssignment = {
          id: uid("CA-"),
          courseId,
          employeeName: employee,
          status: "Complete",
          assignedAt: nowIso(),
        };
        set((s) => ({
          courseAssignments: [...s.courseAssignments, a],
          courses: s.courses.map((c) =>
            c.id === courseId ? { ...c, complete: Math.min(c.enrolled || 1, c.complete + 1) } : c,
          ),
        }));
        get().logAction(employee, "Completed course", courseId);
      },
      bumpCourseProgress: (courseId, delta) => {
        set((s) => ({
          courses: s.courses.map((c) =>
            c.id === courseId
              ? { ...c, complete: Math.max(0, Math.min(c.enrolled, c.complete + delta)) }
              : c,
          ),
        }));
      },

      /* ---------- Settings ---------- */
      updateWorkspaceSettings: (patch) => {
        set((s) => ({ workspaceSettings: { ...s.workspaceSettings, ...patch } }));
        get().logAction("Admin", "Updated workspace settings", "workspace");
      },
      updateEmailSettings: (patch) => {
        set((s) => ({ emailSettings: { ...s.emailSettings, ...patch } }));
        get().logAction("Admin", "Updated email & SMTP settings", "email");
      },
      sendTestEmail: (to) => {
        const target = to || get().emailSettings.fromEmail;
        get().logAction("Admin", `Sent test email to ${target}`, "email-test");
      },
      toggleNotificationTrigger: (id) => {
        set((s) => ({
          notificationTriggers: s.notificationTriggers.map((t) =>
            t.id === id ? { ...t, on: !t.on } : t,
          ),
        }));
        const t = get().notificationTriggers.find((x) => x.id === id);
        get().logAction("Admin", `${t?.on ? "Enabled" : "Disabled"} notification: ${t?.name}`, id);
      },
      updateSecuritySettings: (patch) => {
        set((s) => ({ securitySettings: { ...s.securitySettings, ...patch } }));
        get().logAction("Admin", "Updated security settings", "security");
      },
      toggleIntegration: (name) => {
        set((s) => ({
          integrations: s.integrations.map((i) =>
            i.name === name ? { ...i, on: !i.on } : i,
          ),
        }));
        const i = get().integrations.find((x) => x.name === name);
        get().logAction("Admin", `${i?.on ? "Connected" : "Disconnected"} ${name}`, name);
      },

      /* ---------- Benefits ---------- */
      addBenefit: (p) => {
        const eligible = get().employees.length;
        const id = `BT-${String(get().benefitTypes.length + 1).padStart(2, "0")}`;
        const rec: BenefitType = {
          id,
          name: p.name,
          provider: p.provider,
          enrolled: 0,
          eligible,
          cost: p.cost,
          waitDays: p.waitDays,
          rules:
            p.rule ||
            ({
              eligibility: `All FT after ${p.waitDays} days`,
              approval: "HR → Finance",
              documents: "Invoice + ID",
              waitDays: p.waitDays,
            } as BenefitRule),
        };
        set((s) => ({ benefitTypes: [rec, ...s.benefitTypes] }));
        get().logAction("Admin", "Added benefit", id);
        return rec;
      },
      updateBenefitRule: (id, rule) => {
        set((s) => ({
          benefitTypes: s.benefitTypes.map((b) =>
            b.id === id ? { ...b, rules: rule, waitDays: rule.waitDays } : b,
          ),
        }));
        get().logAction("Admin", "Updated benefit rules", id);
      },
      enrolBenefit: (p) => {
        // Don't double-enrol.
        if (
          get().benefitEnrolments.some(
            (e) => e.benefitId === p.benefitId && e.employee === p.employee,
          )
        ) {
          return null;
        }
        const rec: BenefitEnrolment = {
          id: uid("BE-"),
          benefitId: p.benefitId,
          employee: p.employee,
          plan: p.plan,
          enrolledAt: nowIso(),
        };
        set((s) => ({
          benefitEnrolments: [...s.benefitEnrolments, rec],
          benefitTypes: s.benefitTypes.map((b) =>
            b.id === p.benefitId ? { ...b, enrolled: Math.min(b.eligible, b.enrolled + 1) } : b,
          ),
        }));
        get().logAction(p.employee, `Enrolled in benefit`, p.benefitId);
        return rec;
      },
      unenrolBenefit: (enrolmentId) => {
        const e = get().benefitEnrolments.find((x) => x.id === enrolmentId);
        if (!e) return;
        set((s) => ({
          benefitEnrolments: s.benefitEnrolments.filter((x) => x.id !== enrolmentId),
          benefitTypes: s.benefitTypes.map((b) =>
            b.id === e.benefitId ? { ...b, enrolled: Math.max(0, b.enrolled - 1) } : b,
          ),
        }));
        get().logAction(e.employee, "Unenrolled from benefit", e.benefitId);
      },

      /* ---------- Imports ---------- */
      runImport: (p) => {
        const rec: ImportBatch = {
          id: `IM-${new Date().getFullYear()}-${String(get().importBatches.length + 4).padStart(2, "0")}`,
          type: p.type,
          by: p.by,
          rows: `${p.rows} of ${p.rows}`,
          status: p.status || "Complete",
          when: todayShort() + " · " + new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }),
        };
        set((s) => ({ importBatches: [rec, ...s.importBatches] }));
        get().logAction(p.by, `Ran import (${p.type})`, rec.id);
        return rec;
      },

      /* ---------- Reports ---------- */
      saveReport: (p) => {
        const rec: SavedReport = {
          id: uid("R-"),
          name: p.name,
          group: p.group,
          createdAt: nowIso(),
          favourite: false,
        };
        set((s) => ({ savedReports: [rec, ...s.savedReports] }));
        return rec;
      },
      toggleFavouriteReport: (id) => {
        set((s) => ({
          savedReports: s.savedReports.map((r) =>
            r.id === id ? { ...r, favourite: !r.favourite } : r,
          ),
        }));
      },

      /* ---------- Payroll ---------- */
      startPayrollRun: (period) => {
        const id = `PP-${new Date().getFullYear()}-${String(get().payrollPeriods.length + 5).padStart(2, "0")}`;
        const headcount = get().employees.length;
        const rec: PayrollPeriod = {
          id,
          period,
          status: "Processing",
          employees: headcount,
          gross: `$${(headcount * 9800).toLocaleString()}`,
          net: `$${(headcount * 7200).toLocaleString()}`,
          cutoff: new Date().toISOString().slice(0, 10),
          paydate: new Date(Date.now() + 4 * 86_400_000).toISOString().slice(0, 10),
        };
        set((s) => ({ payrollPeriods: [rec, ...s.payrollPeriods] }));
        get().logAction("Payroll", "Started payroll run", id);
        return rec;
      },
      approvePayrollRun: (id) => {
        set((s) => ({
          payrollPeriods: s.payrollPeriods.map((p) =>
            p.id === id ? { ...p, status: "Paid" } : p,
          ),
        }));
        get().logAction("CFO", "Approved payroll run", id);
      },

      /* ---------- Attendance ---------- */
      clockIn: (who) => {
        set({ clock: { who, clockedInAt: new Date().toISOString() } });
        get().logAction(who, "Clocked in", who);
      },
      clockOut: () => {
        const c = get().clock;
        if (!c.who) return;
        set({ clock: { who: c.who, clockedInAt: null } });
        get().logAction(c.who, "Clocked out", c.who);
      },
      addAttendanceManualEntry: (p) => {
        const rec: AttendanceRow = { ...p };
        set((s) => ({ attendanceToday: [rec, ...s.attendanceToday] }));
        return rec;
      },

      /* ---------- Performance ---------- */
      startReview: (p) => {
        const id = `PR-${Math.floor(Math.random() * 9000 + 1000)}`;
        const rec: PerformanceReview = {
          id,
          who: p.who,
          av: p.av,
          cycle: p.cycle,
          rating: null,
          status: "Self-Assessment",
          manager: p.manager,
          due: p.due,
        };
        set((s) => ({ performanceReviews: [rec, ...s.performanceReviews] }));
        get().logAction(p.manager, "Started review", id);
        return rec;
      },
      setReviewRating: (id, rating) =>
        set((s) => ({
          performanceReviews: s.performanceReviews.map((r) => (r.id === id ? { ...r, rating } : r)),
        })),
      setReviewStatus: (id, status) =>
        set((s) => ({
          performanceReviews: s.performanceReviews.map((r) => (r.id === id ? { ...r, status } : r)),
        })),

      /* ---------- Audit ---------- */
      logAction: (actor, action, entity) => {
        const rec: AuditLog = {
          id: uid("AL-"),
          at: nowAuditTime(),
          actor,
          action,
          entity,
          ip: "10.0.0.1",
        };
        set((s) => ({ auditLogs: [rec, ...s.auditLogs].slice(0, 500) }));
      },

      /* ---------- Reset ---------- */
      resetAll: () => set(initialSeed()),
    }),
    {
      name: "bunchly.runtime.v2",
      // Only persist data collections; actions are rebuilt by the factory.
      partialize: (s) => ({
        employees: s.employees,
        leaveRequests: s.leaveRequests,
        documents: s.documents,
        candidates: s.candidates,
        jobReqs: s.jobReqs,
        onboardingProgrammes: s.onboardingProgrammes,
        onboardingTasks: s.onboardingTasks,
        policies: s.policies,
        policyAcknowledgements: s.policyAcknowledgements,
        hrCases: s.hrCases,
        assets: s.assets,
        courses: s.courses,
        courseAssignments: s.courseAssignments,
        benefitTypes: s.benefitTypes,
        benefitEnrolments: s.benefitEnrolments,
        workspaceSettings: s.workspaceSettings,
        emailSettings: s.emailSettings,
        notificationTriggers: s.notificationTriggers,
        securitySettings: s.securitySettings,
        integrations: s.integrations,
        educationClaims: s.educationClaims,
        payrollPeriods: s.payrollPeriods,
        performanceReviews: s.performanceReviews,
        auditLogs: s.auditLogs,
        attendanceToday: s.attendanceToday,
        interviews: s.interviews,
        importBatches: s.importBatches,
        savedReports: s.savedReports,
        clock: s.clock,
      }),
      version: 2,
    },
  ),
);
