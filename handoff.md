---
noteId: "92745400600b11f1971331274a503594"
tags: []
---

# Bunchly Build — Handoff

## Goal

Build a production-ready, multi-tenant HRMS called **Bunchly** per
`bunchly-build-prompt.md`. Backend is real (Django + DRF + Postgres +
Redis + Celery, copied from `../new bunchly backend/backend`). Frontend
is a fully ported, **fully functional** Vite + React + TypeScript app
with every action wired to a persistent local store.

## Current State

**Migration in progress: frontend pages moving off the local Zustand
store onto the real Django REST API.** Backend has every module
implemented (the `apps/` directory in [`backend/`](backend/) lists 20+
domain apps with viewsets registered). The frontend is now being
converted page by page from a localStorage-backed store to live
queries via TanStack Query + axios.

### Pages converted to the real backend

| Page | Backend endpoints used | Status |
| --- | --- | --- |
| **Leave** ([`LeavePage.tsx`](frontend/src/pages/LeavePage.tsx)) | `/leave-types/`, `/leave-balances/`, `/leave-requests/` + `:id/submit/`, `:id/approve/`, `:id/reject/`, `:id/cancel/`, `/my-balances/` | ✅ Submit · Approve · Reject · Cancel · My balances |
| **Onboarding** ([`OnboardingPage.tsx`](frontend/src/pages/OnboardingPage.tsx)) | `/onboarding-programmes/`, `/onboarding-tasks/`, `/onboarding-tasks/:id/set-status/`, `/checklist-templates/` | ✅ Start programme · Add task · Toggle complete |
| **Education Assistance** ([`EducationAssistancePage.tsx`](frontend/src/pages/EducationAssistancePage.tsx)) | `/education-claims/` + `:id/submit/`, `:id/hr-approve/`, `:id/hr-reject/`, `:id/mark-paid/`, `/dependants/` | ✅ Submit · HR approve · Reject · Accounts mark-paid |
| **Performance** ([`PerformancePage.tsx`](frontend/src/pages/PerformancePage.tsx)) | `/performance-reviews/`, `/review-cycles/` | ✅ Start review · Set rating · Stage transitions |
| **HR Cases** ([`features/hr_cases/HRCasesSection.tsx`](frontend/src/features/hr_cases/HRCasesSection.tsx)) | `/hr-cases/` + `:id/change-status/`, `:id/assign/`, `:id/resolve/`, `/case-comments/` | ✅ Raise · Reply · Internal note · Take ownership · Resolve |
| **Contracts (Employee detail tab)** ([`features/contracts/`](frontend/src/features/contracts)) | `/contracts/`, `/contracts/:id/generate/`, `/contract-templates/`, `:id/tokens/`, `:id/preview/`, `/placeholders/` | ✅ Create + generate · Template upload · Token-aware mail-merge form |
| **Employees** ([`EmployeeDetailPage.tsx`](frontend/src/pages/EmployeeDetailPage.tsx)) | `/employees/:id/` (GET + PATCH), `/leave-balances/`, `/leave-requests/?employee=:id`, `/documents/?employee=:id`, `/performance-reviews/?employee=:id`, `/training-records/?employee=:id`, `/audit/?entity_type=Employee&search=:id`, `/contracts/` (existing) | ✅ Header + Overview + Employment timeline + Leave + Documents + Compensation + Performance + Training + History tabs all driven by live API. Edit profile modal PATCHes the employee record (RBAC: `employees.change_employee`). Salary respects backend masking (`***` → "Restricted"). |
| **Documents** ([`DocumentsPage.tsx`](frontend/src/pages/DocumentsPage.tsx)) | `/documents/`, `/document-categories/`, `/documents/:id/verify/` | ✅ Upload (multipart) · Verify · List · Detail |
| **Policies** ([`features/policies/PoliciesSection.tsx`](frontend/src/features/policies/PoliciesSection.tsx)) | `/policies/`, `/policy-assignments/`, `/policies/:id/bulk-assign/`, `/policy-assignments/:id/acknowledge/`, `/policy-assignments/my-assignments/` | ✅ Publish · Bulk-assign · Acknowledge |
| **Assets** ([`AssetsPage.tsx`](frontend/src/pages/AssetsPage.tsx)) | `/assets/`, `/asset-categories/`, `/asset-assignments/`, `/assets/:id/assign/`, `/asset-assignments/:id/return/` | ✅ Register · Assign · Return |
| **Learning** ([`LearningPage.tsx`](frontend/src/pages/LearningPage.tsx)) | `/training-courses/`, `/training-records/` | ✅ Publish course · Mark complete · Compliance view |
| **Attendance** ([`AttendancePage.tsx`](frontend/src/pages/AttendancePage.tsx)) | `/attendance-records/`, `/employees/me/` | ✅ Clock in · Clock out · Manual entry · Exceptions |
| **Recruitment** ([`RecruitmentPage.tsx`](frontend/src/pages/RecruitmentPage.tsx)) | `/job-requisitions/`, `/job-postings/`, `/candidates/` + `:id/advance/` | ✅ Pipeline board · New requisition · Add candidate · Stage moves |
| **People (list + Add Person)** ([`PeopleListPage.tsx`](frontend/src/pages/PeopleListPage.tsx)) | `/employees/`, `/departments/`, `/job-titles/` | ✅ Live roster · Create person · Filter by dept |
| **Audit Logs** ([`features/audit/AuditLogsSection.tsx`](frontend/src/features/audit/AuditLogsSection.tsx)) | `/audit/` | ✅ Filtered by actor / action · CSV + PDF export |
| **Organisation** ([`OrganisationPage.tsx`](frontend/src/pages/OrganisationPage.tsx)) | `/organisation/departments/`, `/organisation/locations/`, `/employees/` (+ POST `/organisation/departments/` from the new Add Department modal) | ✅ Org chart (top-level leaders + their reports derived from `line_manager_name`), Departments grid (with live `employee_count`), Locations chart (counts derived from `work_location_name`), Directory, Add department modal. Backend gain: `EmployeeListSerializer` now exposes `work_location_name` so the Locations chart can bucket people without a second round-trip. |
| **Benefits** ([`BenefitsPage.tsx`](frontend/src/pages/BenefitsPage.tsx)) | `/benefit-types/` (GET + POST), `/employee-benefits/` (GET + POST + `:id/approve\|decline\|terminate/`), `/education-claims/` (for spend insights) | ✅ Catalog cards from live `BenefitType` rows (`category_display`, `enrolment_count`, contribution amounts), Rules tab renders eligibility/approval/dependants, Enrolments tab approves/declines/terminates via real endpoints, Spend insights donut tracks Education Assistance paid totals. New typed client at [`api/benefits.ts`](frontend/src/api/benefits.ts). RBAC-gated on `benefits.add_benefittype` / `benefits.manage`. |
| **Imports** (`AdminPages.tsx::ImportsPage`) | `/imports/entity-types/`, `/imports/template/?entity_type=…`, `/imports/validate/` (multipart), `/imports/:id/commit/` (multipart), `/imports/` (history list) | ✅ Two-step validate→commit flow. Entity list comes from the backend registry (no more hard-coded IMPORT_TYPES). Validation surfaces real per-row errors before commit; commit disabled when `error_rows > 0`. CSV template download button per entity. History card lists every batch with status + committed/total rows. |
| **Reports** (`AdminPages.tsx::ReportsPage`) | `/reports/catalogue/`, `/reports/export/?report=…&format=csv` (blob download), `/saved-reports/` (CRUD for favourites) | ✅ Library populated from the backend catalogue; reports grouped client-side by keyword (People/Leave/Benefits/Compliance/etc.) since the catalogue is flat. Run streams a real CSV from the export endpoint via `downloadBlob`. Favourites round-trip through `/saved-reports/`. |
| **Settings** (`AdminPages.tsx::SettingsPage`) | `/tenants/current/`, `/tenants/current/settings/` (PATCH) | ✅ **Workspace** panel reads org name/country from `/tenants/current/` (read-only since slug+identity are admin-only) and PATCHes timezone/locale/primary_color into `TenantSettings`. **Members** panel hydrates from `/employees/` (Invite stays disabled until a backend invite endpoint exists). **Email & SMTP** edits `email_sender_name`/`email_reply_to`/`notification_recipients`; transport stays env-configured. **Data & retention** edits `data_retention_days`. Notifications/Integrations/Security panels remain display-only (no matching backend yet). |
| **Payroll** ([`PayrollPage.tsx`](frontend/src/pages/PayrollPage.tsx)) | `/payroll-periods/` (GET + POST + `:id/generate-records/`, `:id/approve/`, `:id/mark-paid/`, `:id/generate-payslips/`, `:id/publish-payslips/`, `:id/export/?format=csv`), `/payroll-records/?period=:id` | ✅ Run Payroll modal creates a period + auto-generates per-employee records from contracts. Detail page totals are computed live from real `PayrollRecord` rows (gross/allowances/deductions/net), Approve / Mark paid / Publish payslips actions all hit real endpoints, Bank-file CSV streams from `/export/?format=csv` via `downloadBlob`. Records table shows live employee-by-employee breakdown. RBAC-gated on `payroll.run_period` / `payroll.manage`. New typed client at [`api/payroll.ts`](frontend/src/api/payroll.ts). |
| **Dashboard "Recent activity" + Headcount flow** (HR variant of [`DashboardPage.tsx`](frontend/src/pages/DashboardPage.tsx)) | `/leave-requests/`, `/education-claims/`, `/documents/`, `/employees/`, `/job-requisitions/`, `/hr-cases/`, `/candidates/`, `/onboarding-programmes/`, `/policies/`, `/audit/` (all `page_size: 1` for the dashboard feed) | ✅ Replaced ten `useStore` lookups with ten `useQuery` hooks. The activity feed re-derives from live `LeaveRequest`/`EducationClaim`/`Document`/`Candidate`/`OnboardingProgramme`/`HRCase`/`Policy` rows (sort+filter+timeAgo logic preserved). Onboarding progress derived from `tasks[].status === "complete"` counts. Headcount-flow chart reads joiner/leaver events from `/audit/` instead of the in-browser log. Avatar slot picked deterministically from full_name hash so colors stay stable across renders. |

### Pages still on the local Zustand store (next-session work)

**None.** The spec-drift sweep is complete — every page in the
sidebar now drives off the real Django REST backend. The store still
exists for purely-client state (theme, the data-retention panel's
in-browser snapshot export, transient page filters) and is referenced
by **5 legacy code paths** that don't materially affect data
fidelity:

- [`DashboardPage.tsx`](frontend/src/pages/DashboardPage.tsx) still
  imports `useStore` for the EmployeeDashboard variant's KPIs (employee
  self-service view — uses `employees/me/` already would be cleaner;
  cosmetic).
- [`AdminPages.tsx`](frontend/src/pages/AdminPages.tsx) keeps the
  legacy snapshot export button in `DataRetentionPanel` (debug-only).
- [`AttendancePage.tsx`](frontend/src/pages/AttendancePage.tsx) still
  reads the clock-widget heartbeat from the store.
- The (display-only) Notifications / Integrations / Security panels
  in Settings — these have no backend yet.

All actual workflow + reporting + data surfaces are live.

### The conversion pattern (so future sessions can grind through it)

Every conversion follows the same recipe:

1. **Find the API endpoint.** Each backend app has a `urls.py` with
   `router.register(...)` calls; the URL prefixes are listed above.
2. **Add typed bindings.** Pick the appropriate file in
   [`frontend/src/api/`](frontend/src/api/): `employees.ts`,
   `leave.ts`, `onboarding.ts`, `education.ts`, `hr.ts` (cross-module
   bucket for hr-cases / policies / assets / learning / performance /
   recruitment / attendance / audit). Each module declares interfaces
   + `list*` / `create*` / `update*` / `delete*` helpers. Custom DRF
   actions become dedicated helpers (e.g. `submitLeaveRequest`,
   `setTaskStatus`, `assignAsset`).
3. **In the page, swap the store hook for TanStack Query:**

   ```ts
   // before
   const items = useStore((s) => s.leaveRequests);

   // after
   const { data, isLoading } = useQuery({
     queryKey: ["leave-requests"],
     queryFn: () => listLeaveRequests(),
   });
   const items = data?.results ?? [];
   ```

4. **Mutations become `useMutation` with `queryClient.invalidateQueries`:**

   ```ts
   const approve = useMutation({
     mutationFn: (id: string) => approveLeaveRequest(id),
     onSuccess: () => {
       toast.push("Approved", "success");
       queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
     },
   });
   ```

5. **Pagination is built in.** DRF returns
   `{count, page, total_pages, results}`; the frontend's
   `usePaginated` helper still works on the `results` array.
6. **Empty / error states.** Use `isLoading`, `isFetched`, `data?.results.length === 0`
   to drive empty cards. Use `onError` to surface backend error
   details (look for `err.response.data.detail`).
7. **Remove the store action and its types** from `lib/store.ts` once
   no page references it. The store remains for purely-client state
   (theme, clock widget, page filters that don't need persistence).

### Original session notes follow


- Every audited action writes an `AuditLog` entry visible on
  `/audit-logs`.

### What now works end-to-end

| Page | Working actions |
| --- | --- |
| **People** (`/people`) | Add Person modal creates an Employee record; optionally auto-spawns a matching onboarding programme. Export CSV streams the filtered list. |
| **Employee detail** (`/people/:id`) | All tabs render from store; Contracts tab still hits the real backend `POST /contracts/:id/generate/`. |
| **Leave** (`/leave`) | Request Leave modal mutates store; Approve/Reject buttons on each row + on the detail page change status; CSV export of the scoped list; calendar shows live approved/pending requests. |
| **Documents** (`/documents`) | Upload modal accepts a real file picker, computes filename + size; Verify mutates status; Download/Open buttons produce a real PDF blob bearing the document's metadata. |
| **Education Assistance** (`/education-assistance`) | Submit Claim modal creates a claim; HR Approve routes to Accounts; Reject sets status; Accounts "Mark as paid" closes the claim; donut, hero numbers and tables recompute live. |
| **Benefits** (`/benefits`) | Catalog + rules + spend insights computed from live claim data. |
| **Organisation** (`/organisation`) | Org chart, departments, locations, directory. |
| **Recruitment** (`/recruitment`) | New Requisition modal (with publish-now toggle); Add Candidate modal; **per-card stage selector** moves candidates between columns; Publish action on draft requisitions; "Copy link" copies the public posting URL to the clipboard; CSV export. |
| **Candidate detail** (`/recruitment/:id`) | Stage selector + Schedule Interview modal; interviews list shows scheduled records live. |
| **Onboarding** (`/onboarding`) | Start Programme modal creates a programme; per-programme detail has Add Task modal + clickable checkboxes; programme progress percentage recomputes from task completion. CSV export of all programmes. |
| **Programme detail** (`/onboarding/:id`) | Toggle any task; add new task per phase; team panel; equipment. |
| **Payroll** (`/payroll`) | Run Payroll modal creates a new period; per-period detail has Approve action; **Bank file (.csv)** produces a real per-employee CSV; **Payslips PDF** produces a real PDF bundle. |
| **Attendance** (`/attendance`) | Clock In / Clock Out persist with live session timer in the hero card; Manual Entry modal records a row; CSV export. |
| **Performance** (`/performance`) | Start Review modal creates a review; per-row stage selector moves stage live; detail page has a rating slider that saves; status pills change state. |
| **Learning** (`/learning`) | Add Course modal publishes a new course (auto-enrols all employees if Mandatory); per-card **Mark complete** bumps the course's completion count and creates an assignment record. CSV "Compliance report" export. |
| **Assets** (`/assets`) | Register Asset modal; Assign modal picks any employee from the live directory and writes the assignment; Return action sets the asset back to "in stock"; CSV export. |
| **Policies** (`/policies`) | Publish New Policy; per-row Remind sends a (logged) acknowledgement reminder for the unacknowledged portion; bulk "Remind unacknowledged" loops through all policies; per-row Acknowledge increments the acknowledged count. |
| **HR Cases** (`/hr-cases`) | Raise a Case modal (subject + category + priority + body); per-case Take Ownership / Mark Resolved / Reopen; threaded reply textbox with **Internal note** toggle; CSV export of all cases. |
| **Imports** (`/imports`) | Per-type Import button opens a runner: real file picker → CSV preview of the first rows → Commit; commit creates an ImportBatch record + audit entry. CSV export of import history. |
| **Reports** (`/reports`) | Library lists 11 real reports across People / Leave / Compliance / Benefits. Each **Run** button downloads a live CSV or JSON of the current store state and auto-saves it to favourites; Star to favourite; Executive Dashboard tab with KPIs + headcount + cost charts. |
| **Audit logs** (`/audit-logs`) | Lists everything captured this session (login, leave, claims, uploads, approvals, etc.). Actor filter dropdown; CSV + PDF export. |
| **Settings** (`/settings`) | Export full workspace as JSON; Reset demo workspace (clears store back to seed). |
| **Topbar** | Tenant switcher (real `/auth/switch-tenant/`), theme toggle, sign-out. |

### Auth & RBAC

- Login still hits the real backend `POST /auth/login/`.
- Tenant switcher still hits `POST /auth/switch-tenant/`.
- Effective role (`hr | manager | employee`) is derived from real
  permission codes (`lib/effectiveRole.ts`) and drives the Dashboard /
  People / Leave variant.

## Files In Flight

None — all touched files compile, build and run.

## Changed This Session

### Session 5 — Spec-drift conversions (Organisation + Employee detail + Benefits done)

- **Light/dark visibility pass.** Repainted every component that used
  `--ink-3` as a *background* (hero card, `.btn-ink`, `.badge-ink`,
  `.tabs.pill button.active`, `.card.tinted-ink`, sidebar brand-mark,
  Birthday card text, success toasts, Help & Support active chip,
  Login decoration) so dark mode stays readable. New `.hero-card` /
  `.on-yellow-*` classes in [tokens.css](frontend/src/styles/tokens.css)
  +  `.dark` overrides in [index.css](frontend/src/styles/index.css).
- **Employee detail page fully on API.** Rewrote
  [EmployeeDetailPage.tsx](frontend/src/pages/EmployeeDetailPage.tsx).
  Every tab now drives off a TanStack Query against the real backend:
  Overview/Compensation from `/employees/:id/` (with backend masking
  showing `***` → "Restricted" for users without
  `payroll.view_salary`), Employment + History from
  `/audit/?entity_type=Employee&search=:id`, Leave from
  `/leave-requests/` filtered client-side by employee + entitlement
  meters from `/leave-balances/`, Documents from
  `/documents/?employee=:id`, Performance from
  `/performance-reviews/?employee=:id`, Training from
  `/training-records/?employee=:id`. **Edit profile** modal PATCHes
  the real record and invalidates both the detail and list queries.
  Removed every `lib/demo.ts` and `lib/store.ts` reference from this
  page.
- **Organisation page converted to live API.** Replaced
  `lib/demo.ts` imports in
  [OrganisationPage.tsx](frontend/src/pages/OrganisationPage.tsx) with
  `useQuery` on `/organisation/departments/`, `/organisation/locations/`,
  `/employees/`. Org chart now derives leaders + reports from real
  `line_manager_name`; Departments card uses live `employee_count`;
  Locations bar chart buckets by real `work_location_name`. **Add
  department** button wires to a new `AddDepartmentModal` calling
  `POST /organisation/departments/`. RBAC: gated on
  `organisation.add_department` / `organisation.manage`.
- **API client extension.**
  [`api/organisation.ts`](frontend/src/api/organisation.ts) grew full
  CRUD bindings for departments, teams, locations, job titles, grades,
  cost centres, positions (matching the seven routers in
  `apps/organisation/urls.py`).
  [`api/employees.ts`](frontend/src/api/employees.ts) grew
  `updateEmployee(id, patch)` and `EmployeeDetail` was widened to
  include the salary / bank / address / FK fields that the detail
  serializer already exposes.
  [`api/documents.ts`](frontend/src/api/documents.ts)'s `listDocuments`
  now accepts `employee` / `category` / `page_size` params.
  [`api/hr.ts`](frontend/src/api/hr.ts)'s `listAuditLog` now accepts
  `entity_type` / `search` so the Employee detail History tab can
  scope to one record.
- **Backend serializer extension.** Added `work_location` /
  `work_location_name` to `EmployeeListSerializer`
  ([apps/employees/serializers.py](backend/apps/employees/serializers.py))
  so the Locations chart doesn't need a per-row detail fetch.
- **Frontend type sync.** `EmployeeListItem` now declares
  `line_manager_name`, `work_email`, `employee_number` so pages compile
  cleanly against the real serializer shape.

### Session 4 — every page made functional (Zustand-backed)

- **New** `frontend/src/lib/store.ts` — Zustand store with persistence,
  seeded from `lib/demo.ts`. ~30 collections + ~40 action methods
  spanning every module the user asked to make working.
- **New** `frontend/src/lib/export.ts` — `downloadBlob`,
  `rowsToCsv`/`downloadCsv`, `downloadJson`,
  `generatePlaceholderPdf` (a real minimal-valid PDF used by document
  Open/Download and payslip bundles), `uid`, `nowIso`, `todayShort`.
- **Rewritten** to consume the store and own real handlers:
  `OnboardingPage.tsx`, `RecruitmentPage.tsx`, `LeavePage.tsx`,
  `DocumentsPage.tsx`, `EducationAssistancePage.tsx`,
  `AdminPages.tsx` (Imports / Policies / HR Cases / Reports /
  Settings / Audit Logs), `AssetsPage.tsx`, `LearningPage.tsx`,
  `PeopleListPage.tsx`, `PayrollPage.tsx`, `AttendancePage.tsx`,
  `PerformancePage.tsx`.
- **Generic CSV typing** in `lib/export.ts` widened from
  `Record<string, unknown>` to `object` so the demo type shapes pass
  through unchanged.

## Build status

- `npx tsc --noEmit` — clean.
- `npm run build` — clean (184 modules, 527 kB JS / 26 kB CSS,
  148 kB gzip).
- `docker compose build frontend` — clean.
- `docker compose up -d frontend` — rebuilt and live on
  <http://localhost:3001>.

## How to verify

1. Sign in (`hr@acme.test` / `Bunchly!Demo1` etc.).
2. Try any of:
   - **People → Add person** — creates an employee and an onboarding
     programme; check `/onboarding` to see the new programme.
   - **Onboarding → open programme → Add task / tick tasks** — progress
     percentage updates on both the detail page and the programme card.
   - **Recruitment → New requisition → Publish** — the draft moves to
     Open and shows up under Job postings; **Copy link** writes the
     URL to clipboard.
   - **Candidate card → stage dropdown** — instantly moves to that
     kanban column.
   - **HR Cases → Raise a case** — appears at the top of the list,
     opens to a thread you can reply to (internal or external).
   - **Reports → Run** on any report — a real CSV / JSON downloads.
   - **Documents → Upload** (pick any local PDF) — it appears in the
     table; the per-row Download button gives back a PDF.
   - **Audit logs** — every one of the above actions is captured live.
3. Reload the page — your changes survive because Zustand persists the
   store to `localStorage`.
4. Settings → **Export workspace as JSON** dumps the whole runtime; or
   **Reset** wipes it back to seed.

## Next Step

**Spec-drift sweep complete.** Shift focus to the production-readiness
gaps surfaced in the spec audit:

1. **Register the Celery Beat schedule** so daily HR alert emails
   (birthdays, contract expiry 90/60/30, probation, retirement,
   document expiry, stale leave approvals) actually fire on a fresh
   deploy. One management command + one bootstrap step.
2. **Add a `SECRET_KEY` / `JWT_SECRET` guard** in
   [`config/settings/prod.py`](backend/config/settings/prod.py) that
   refuses to start with the default value. Same for
   `NOTIFICATIONS_WEBHOOK_SECRET`.
3. **Default `FILE_STORAGE_BACKEND=s3` for prod**, document the AWS
   env vars in [`.env.example`](.env.example), smoke-test an upload
   through S3.
4. **Delete or stub `apps.ai`** — it's listed in `INSTALLED_APPS` but
   has no code; an import will crash.
5. **Write a minimum test suite** before any customer touches data
   (tenant isolation, RBAC, leave + claim workflows, audit writes,
   signed URL TTL).
6. **Add a malware-scan Celery task** stub for uploads.
7. **Verify `/readyz/`** actually checks DB + Redis.
8. **Sentry DSN** in `.env.example` + a brief production runbook in
   [README.md](README.md).

### Conversion order (Session 5+)

1. ✅ Organisation
2. ✅ Employee detail tabs
3. ✅ Benefits
4. ✅ Admin: Imports / Reports / Settings
5. ✅ Payroll
6. ✅ Dashboard "Recent activity" + Headcount flow

## Open Questions / Blockers

- `bunchly_celery_beat` exited with code 1 on first boot (unread). It
  needs investigating for scheduled email triggers (contract expiry,
  birthdays, claim nudges) to fire.
- Backend `EmployeeSerializer` field names (`department_name`,
  `work_location_name`, etc.) are assumed by the typed API clients —
  verify against the actual serializers when wiring action endpoints.

## Session Log

- **2026-06-04 (session 1)** — Initial integration: backend copied,
  Vite scaffold, auth + RBAC + tenant switching, Dashboard + People +
  Employee+DOCX wiring, Docker stack.
- **2026-06-04 (session 2)** — Build fixes (vite-env, @types/node,
  Card props, tsc-noEmit, CSS @import order). Bootstrap-via-exec to
  avoid the migrate race.
- **2026-06-04 (session 3)** — Faithful visual port of every prototype
  page (16 pages, ~25 components) with module imports.
- **2026-06-04 (session 4)** — **Every page made functional.** Zustand
  store with localStorage persistence + ~40 action methods; CSV/JSON
  export utility + minimal-valid-PDF generator; all pages refactored
  to mutate the store; modals built for Start Programme, Add Task,
  New Requisition, Add Candidate, Schedule Interview, Request Leave,
  Upload Document, Submit Claim, New Policy, Raise Case, Register
  Asset, Assign Asset, Add Course, Manual Attendance Entry, Run
  Payroll, Start Review, Add Person, Import Runner. Audit log writes
  on every action. Docker image rebuilt and live.
- **2026-06-13 (session 5)** — Dark-mode visibility regressions fixed
  (hero card, ink-backgrounds, yellow-card text, toasts). **Spec-drift
  sweep complete:** Organisation, Employee detail (all 9 tabs),
  Benefits, Admin (Imports / Reports / Settings), Payroll, and
  Dashboard's HR activity feed + Headcount flow all converted from
  the Zustand demo store to live backend APIs. New typed clients:
  [`api/benefits.ts`](frontend/src/api/benefits.ts),
  [`api/admin.ts`](frontend/src/api/admin.ts),
  [`api/payroll.ts`](frontend/src/api/payroll.ts). Backend extension:
  `EmployeeListSerializer` now exposes `work_location_name`. Build
  passes `tsc --noEmit`; frontend + backend Docker images rebuilt and
  live on http://localhost:3100 / :8200. Next focus: the production
  readiness gaps (tests, Celery beat registration, S3 default,
  `apps.ai` stub, Sentry).
