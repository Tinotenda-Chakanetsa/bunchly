/* Cross-module API client modules for: HR cases (helpdesk), policies,
   assets, learning, performance, recruitment, attendance, payroll,
   audit, imports. One file keeps them discoverable without spawning
   eighteen tiny modules. */
import { api } from "./client";
import type { Paginated } from "./employees";

/* ---------- HR Cases (helpdesk) ---------- */
export interface HRCase {
  id: string;
  case_number: string;
  raised_by: string;
  raised_by_name?: string;
  category: string;
  category_name?: string;
  subject: string;
  description: string;
  priority: string;
  status: string;
  status_display?: string;
  assignee?: string | null;
  assignee_name?: string | null;
  sla_due_at?: string | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}
export interface CaseComment {
  id: string;
  case: string;
  author: string;
  author_name?: string;
  body: string;
  is_internal: boolean;
  created_at: string;
}
export interface CaseCategory {
  id: string;
  name: string;
  code: string;
  default_sla_hours?: number;
}
export async function listCaseCategories() {
  const { data } = await api.get<Paginated<CaseCategory>>("/case-categories/", {
    params: { page_size: 200 },
  });
  return data.results;
}
export async function listHRCases(params: { status?: string; page?: number } = {}) {
  const { data } = await api.get<Paginated<HRCase>>("/hr-cases/", { params });
  return data;
}
export async function getHRCase(id: string) {
  const { data } = await api.get<HRCase>(`/hr-cases/${id}/`);
  return data;
}
export async function raiseHRCase(payload: {
  category?: string;
  subject: string;
  description: string;
  priority: "low" | "medium" | "high" | "urgent";
}) {
  const { data } = await api.post<HRCase>("/hr-cases/", payload);
  return data;
}
export async function listCaseComments(caseId: string) {
  const { data } = await api.get<Paginated<CaseComment>>("/case-comments/", {
    params: { case: caseId, page_size: 200 },
  });
  return data.results;
}
export async function addCaseComment(payload: {
  case: string;
  body: string;
  is_internal: boolean;
}) {
  const { data } = await api.post<CaseComment>("/case-comments/", payload);
  return data;
}
export async function changeCaseStatus(id: string, status: string) {
  const { data } = await api.post<HRCase>(`/hr-cases/${id}/change-status/`, {
    status,
  });
  return data;
}
export async function assignCase(id: string, assignee: string) {
  const { data } = await api.post<HRCase>(`/hr-cases/${id}/assign/`, {
    assignee,
  });
  return data;
}
export async function resolveCase(id: string, resolution_summary = "") {
  const { data } = await api.post<HRCase>(`/hr-cases/${id}/resolve/`, {
    resolution_summary,
  });
  return data;
}

/* ---------- Policies ---------- */
export interface Policy {
  id: string;
  title: string;
  code: string;
  category: string;
  category_display?: string;
  description: string;
  owner?: string;
  owner_name?: string;
  requires_acknowledgement: boolean;
  is_active: boolean;
  current_version?: string | null;
  current_version_detail?: PolicyVersion | null;
  assignment_count?: number;
  pending_count?: number;
  created_at: string;
}
export interface PolicyVersion {
  id: string;
  policy: string;
  version: string;
  document?: string;
  effective_date: string;
  change_summary?: string;
  published_at?: string | null;
  is_published: boolean;
}
export interface PolicyAssignment {
  id: string;
  policy: string;
  policy_title?: string;
  policy_code?: string;
  policy_category?: string;
  employee: string;
  employee_name?: string;
  due_date?: string | null;
  acknowledged_at?: string | null;
  acknowledged_version?: string | null;
  current_version?: string;
  is_acknowledged: boolean;
  comment?: string;
}
export async function listPolicies(params: { page?: number } = {}) {
  const { data } = await api.get<Paginated<Policy>>("/policies/", { params });
  return data;
}
export async function createPolicy(payload: {
  title: string;
  code: string;
  category: string;
  description: string;
  requires_acknowledgement?: boolean;
}) {
  const { data } = await api.post<Policy>("/policies/", payload);
  return data;
}
export async function bulkAssignPolicy(
  id: string,
  payload: { employees: string[]; due_date?: string | null },
) {
  const { data } = await api.post<{ assigned: number }>(
    `/policies/${id}/bulk-assign/`,
    payload,
  );
  return data;
}
export async function listMyPolicyAssignments() {
  const { data } = await api.get<Paginated<PolicyAssignment>>(
    "/policy-assignments/my-assignments/",
  );
  return data.results;
}
export async function listPolicyAssignments(policyId?: string) {
  const { data } = await api.get<Paginated<PolicyAssignment>>(
    "/policy-assignments/",
    { params: policyId ? { policy: policyId, page_size: 200 } : { page_size: 200 } },
  );
  return data.results;
}
export async function acknowledgePolicy(assignmentId: string, comment = "") {
  const { data } = await api.post<PolicyAssignment>(
    `/policy-assignments/${assignmentId}/acknowledge/`,
    { comment },
  );
  return data;
}

/* ---------- Assets ---------- */
export interface AssetCategory {
  id: string;
  name: string;
  code: string;
  asset_count?: number;
}
export interface Asset {
  id: string;
  category?: string | null;
  category_name?: string;
  name: string;
  asset_tag: string;
  serial_number: string;
  description?: string;
  status: string;
  status_display?: string;
  condition: string;
  condition_display?: string;
  purchase_date?: string | null;
  purchase_cost?: string;
  currency?: string;
  location?: string;
  notes?: string;
}
export interface AssetAssignment {
  id: string;
  asset: string;
  asset_name?: string;
  asset_tag?: string;
  employee: string;
  employee_name?: string;
  status: string;
  status_display?: string;
  issued_date?: string;
  issued_by?: string;
  issue_condition?: string;
  due_return_date?: string | null;
  returned_date?: string | null;
  return_condition?: string;
  returned_to?: string;
  notes?: string;
}
export async function listAssets(params: { status?: string; page?: number } = {}) {
  const { data } = await api.get<Paginated<Asset>>("/assets/", { params });
  return data;
}
export async function listAssetCategories() {
  const { data } = await api.get<Paginated<AssetCategory>>("/asset-categories/", {
    params: { page_size: 100 },
  });
  return data.results;
}
export async function listAssetAssignments(params: { asset?: string; status?: string } = {}) {
  const { data } = await api.get<Paginated<AssetAssignment>>("/asset-assignments/", {
    params: { ...params, page_size: 500 },
  });
  return data.results;
}
export async function registerAsset(payload: {
  name: string;
  asset_tag: string;
  serial_number: string;
  category?: string;
  condition: string;
  description?: string;
  location?: string;
}) {
  const { data } = await api.post<Asset>("/assets/", payload);
  return data;
}
export async function assignAssetAction(payload: {
  assetId: string;
  employee: string;
  notes?: string;
  due_return_date?: string;
  issue_condition?: string;
}) {
  const { data } = await api.post<AssetAssignment>(
    `/assets/${payload.assetId}/assign/`,
    {
      employee: payload.employee,
      notes: payload.notes,
      due_return_date: payload.due_return_date,
      issue_condition: payload.issue_condition,
    },
  );
  return data;
}
export async function returnAssetAction(payload: {
  assignmentId: string;
  return_condition?: string;
  notes?: string;
}) {
  const { data } = await api.post<AssetAssignment>(
    `/asset-assignments/${payload.assignmentId}/return/`,
    {
      return_condition: payload.return_condition,
      notes: payload.notes,
    },
  );
  return data;
}

/* ---------- Learning ---------- */
export interface TrainingCourse {
  id: string;
  code: string;
  title: string;
  description: string;
  duration_hours: string;
  is_mandatory: boolean;
  validity_period_months?: number | null;
  is_active: boolean;
}
export interface TrainingRecord {
  id: string;
  employee: string;
  employee_name?: string;
  course: string;
  course_title?: string;
  status: string;
  enrolled_at?: string;
  completed_at?: string | null;
  expires_at?: string | null;
  score?: string;
}
export async function listTrainingCourses(params: { page?: number } = {}) {
  const { data } = await api.get<Paginated<TrainingCourse>>(
    "/training-courses/",
    { params },
  );
  return data;
}
export async function createTrainingCourse(payload: {
  code: string;
  title: string;
  description: string;
  duration_hours: number;
  is_mandatory: boolean;
}) {
  const { data } = await api.post<TrainingCourse>("/training-courses/", payload);
  return data;
}
export async function listTrainingRecords(params: { employee?: string; course?: string } = {}) {
  const { data } = await api.get<Paginated<TrainingRecord>>(
    "/training-records/",
    { params },
  );
  return data;
}
export async function markTrainingComplete(payload: {
  course: string;
  employee: string;
  score?: number;
}) {
  const { data } = await api.post<TrainingRecord>("/training-records/", {
    course: payload.course,
    employee: payload.employee,
    status: "complete",
    score: payload.score,
    completed_at: new Date().toISOString(),
  });
  return data;
}

/* ---------- Performance ---------- */
export interface PerformanceReview {
  id: string;
  employee: string;
  employee_name?: string;
  cycle: string;
  cycle_name?: string;
  reviewer?: string;
  reviewer_name?: string;
  status: string;
  status_display?: string;
  overall_rating?: string | null;
  manager_comments?: string;
  employee_comments?: string;
  due_date?: string | null;
  finalised_at?: string | null;
  created_at: string;
}
export interface ReviewCycle {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
}
export async function listPerformanceReviews(params: { status?: string; employee?: string; page?: number } = {}) {
  const { data } = await api.get<Paginated<PerformanceReview>>(
    "/performance-reviews/",
    { params },
  );
  return data;
}
export async function startPerformanceReview(payload: {
  employee: string;
  cycle: string;
  reviewer?: string;
  due_date?: string;
}) {
  const { data } = await api.post<PerformanceReview>(
    "/performance-reviews/",
    payload,
  );
  return data;
}
export async function updatePerformanceReview(
  id: string,
  patch: Partial<PerformanceReview>,
) {
  const { data } = await api.patch<PerformanceReview>(
    `/performance-reviews/${id}/`,
    patch,
  );
  return data;
}
export async function submitPerformanceReview(id: string) {
  const { data } = await api.post<PerformanceReview>(
    `/performance-reviews/${id}/submit/`,
    {},
  );
  return data;
}
export async function acknowledgePerformanceReview(id: string) {
  const { data } = await api.post<PerformanceReview>(
    `/performance-reviews/${id}/acknowledge/`,
    {},
  );
  return data;
}
export async function completePerformanceReview(id: string) {
  const { data } = await api.post<PerformanceReview>(
    `/performance-reviews/${id}/complete/`,
    {},
  );
  return data;
}
export async function listReviewCycles() {
  const { data } = await api.get<Paginated<ReviewCycle>>("/review-cycles/");
  return data.results;
}

/* ---------- Recruitment ---------- */
export interface JobRequisition {
  id: string;
  reference?: string;
  title: string;
  department?: string;
  department_name?: string;
  job_title?: string;
  grade?: string;
  headcount: number;
  employment_type: string;
  hiring_manager?: string;
  status: string;
  status_display?: string;
  reason?: string;
  created_at: string;
}
export interface JobPosting {
  id: string;
  requisition?: string;
  title: string;
  description?: string;
  location?: string | null;
  location_name?: string;
  employment_type?: string;
  is_internal?: boolean;
  status: string;
  status_display?: string;
  posted_date?: string | null;
  closing_date?: string | null;
  candidate_count?: number;
  created_at: string;
}
export interface Candidate {
  id: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  email?: string;
  phone?: string;
  posting?: string | null;
  posting_title?: string;
  stage: string;
  stage_display?: string;
  source?: string;
  rating?: number | null;
  summary?: string;
  notes?: string;
  applied_at?: string | null;
  created_at: string;
}
export async function listJobRequisitions(params: { status?: string; page?: number } = {}) {
  const { data } = await api.get<Paginated<JobRequisition>>(
    "/job-requisitions/",
    { params },
  );
  return data;
}
export async function createJobRequisition(payload: {
  title: string;
  department?: string;
  headcount: number;
  employment_type: string;
  hiring_manager?: string;
  reason?: string;
}) {
  const { data } = await api.post<JobRequisition>("/job-requisitions/", payload);
  return data;
}
export async function listJobPostings(params: { status?: string; page?: number } = {}) {
  const { data } = await api.get<Paginated<JobPosting>>("/job-postings/", {
    params,
  });
  return data;
}
export async function createJobPosting(payload: {
  requisition: string;
  title: string;
  description?: string;
  employment_type?: string;
}) {
  const { data } = await api.post<JobPosting>("/job-postings/", payload);
  return data;
}
export async function listCandidates(params: { stage?: string; page?: number } = {}) {
  const { data } = await api.get<Paginated<Candidate>>("/candidates/", {
    params: { ...params, page_size: 200 },
  });
  return data;
}
export async function createCandidate(payload: {
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  posting?: string;
  source?: string;
  summary?: string;
  notes?: string;
}) {
  const { data } = await api.post<Candidate>("/candidates/", payload);
  return data;
}
export async function moveCandidateStage(id: string, stage: string, reason = "") {
  const { data } = await api.post<Candidate>(`/candidates/${id}/advance/`, {
    stage,
    reason,
  });
  return data;
}

/* ---------- Attendance ---------- */
export interface AttendanceRecord {
  id: string;
  employee: string;
  employee_name?: string;
  work_date: string;
  shift?: string | null;
  shift_name?: string;
  entry_type?: string;
  status: string;
  status_display?: string;
  clock_in?: string | null;
  clock_out?: string | null;
  break_minutes?: number;
  worked_minutes?: number;
  overtime_minutes?: number;
  is_late?: boolean;
  late_minutes?: number;
  approval_status?: string;
  approval_status_display?: string;
  is_exception?: boolean;
  notes?: string;
}
export async function listAttendanceRecords(params: { work_date?: string; employee?: string } = {}) {
  const { data } = await api.get<Paginated<AttendanceRecord>>(
    "/attendance-records/",
    { params: { ...params, page_size: 200 } },
  );
  return data;
}
export async function clockIn() {
  // Backend infers the employee from the JWT and writes today's record.
  const { data } = await api.post<AttendanceRecord>(
    "/attendance-records/clock-in/",
    {},
  );
  return data;
}
export async function clockOut() {
  const { data } = await api.post<AttendanceRecord>(
    "/attendance-records/clock-out/",
    {},
  );
  return data;
}
export async function createManualAttendance(payload: {
  employee: string;
  work_date: string;
  clock_in?: string;
  clock_out?: string;
  status?: string;
  break_minutes?: number;
  notes?: string;
}) {
  const { data } = await api.post<AttendanceRecord>(
    "/attendance-records/",
    payload,
  );
  return data;
}

/* ---------- Audit ---------- */
export interface AuditEntry {
  id: string;
  actor?: string | null;
  actor_name?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  description: string;
  ip_address?: string;
  created_at: string;
}
export async function listAuditLog(
  params: {
    actor?: string;
    action?: string;
    entity_type?: string;
    search?: string;
    page?: number;
    page_size?: number;
  } = {},
) {
  const { data } = await api.get<Paginated<AuditEntry>>("/audit/", { params });
  return data;
}
