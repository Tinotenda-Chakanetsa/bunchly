import { api } from "./client";
import type { Paginated } from "./employees";

export interface LeaveType {
  id: string;
  name: string;
  code: string;
  description?: string;
  default_days_per_year: number;
  is_paid: boolean;
  is_active: boolean;
  requires_document: boolean;
}

export interface LeaveBalance {
  id: string;
  employee: string;
  employee_name?: string;
  leave_type: string;
  leave_type_name?: string;
  year: number;
  entitlement_days: string;
  taken_days: string;
  pending_days: string;
  balance_days: string;
}

export interface LeaveRequest {
  id: string;
  employee: string;
  employee_name?: string;
  leave_type: string;
  leave_type_name?: string;
  status: string;
  status_display?: string;
  start_date: string;
  end_date: string;
  days_requested: string;
  reason: string;
  manager_decision?: string;
  hr_decision?: string;
  submitted_at?: string;
  decided_at?: string;
  decided_by?: string;
  created_at: string;
}

export async function listLeaveTypes() {
  const { data } = await api.get<Paginated<LeaveType>>("/leave-types/", {
    params: { page_size: 50 },
  });
  return data.results;
}

export async function listLeaveRequests(params: {
  status?: string;
  employee?: string;
  search?: string;
  page?: number;
} = {}) {
  const { data } = await api.get<Paginated<LeaveRequest>>("/leave-requests/", {
    params,
  });
  return data;
}

export async function listPendingApprovals() {
  const { data } = await api.get<Paginated<LeaveRequest>>(
    "/leave-requests/pending-approvals/",
  );
  return data.results;
}

export async function listMyLeaveRequests() {
  const { data } = await api.get<Paginated<LeaveRequest>>("/leave-requests/mine/");
  return data.results;
}

export async function listMyLeaveBalances() {
  const { data } = await api.get<Paginated<LeaveBalance>>(
    "/leave-balances/my-balances/",
  );
  return data.results;
}

export async function listLeaveBalances() {
  const { data } = await api.get<Paginated<LeaveBalance>>("/leave-balances/", {
    params: { page_size: 100 },
  });
  return data.results;
}

export async function submitLeaveRequest(payload: {
  employee?: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
}) {
  // Submit creates a draft + immediately submits it. The viewset's
  // create() handles `employee` defaulting to self when omitted.
  const { data } = await api.post<LeaveRequest>("/leave-requests/", payload);
  // Move it from Draft → Submitted via the action endpoint.
  if (data.status === "draft") {
    const { data: submitted } = await api.post<LeaveRequest>(
      `/leave-requests/${data.id}/submit/`,
    );
    return submitted;
  }
  return data;
}

export async function approveLeaveRequest(id: string, comment = "") {
  const { data } = await api.post<LeaveRequest>(
    `/leave-requests/${id}/approve/`,
    { comment },
  );
  return data;
}

export async function rejectLeaveRequest(id: string, reason: string) {
  const { data } = await api.post<LeaveRequest>(
    `/leave-requests/${id}/reject/`,
    { reason },
  );
  return data;
}

export async function cancelLeaveRequest(id: string) {
  const { data } = await api.post<LeaveRequest>(
    `/leave-requests/${id}/cancel/`,
  );
  return data;
}

export async function leaveCalendar(params: { start: string; end: string }) {
  const { data } = await api.get<{ results: Array<{
    id: string;
    employee_name: string;
    leave_type_name: string;
    start_date: string;
    end_date: string;
    days_requested: string;
    status: string;
  }> }>("/leave-requests/calendar/", { params });
  return data.results;
}
