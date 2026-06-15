import { api } from "./client";
import type { Paginated } from "./employees";

export interface PayrollPeriod {
  id: string;
  name: string;
  code: string;
  start_date: string;
  end_date: string;
  pay_date: string;
  status: string;
  status_display?: string;
  notes?: string;
  approved_by?: string | null;
  approved_at?: string | null;
  record_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface PayrollRecord {
  id: string;
  period: string;
  period_name?: string;
  employee: string;
  employee_name?: string;
  currency?: string;
  basic_salary?: string;
  total_allowances?: string;
  total_deductions?: string;
  overtime_amount?: string;
  leave_without_pay_days?: string;
  leave_without_pay_amount?: string;
  gross_pay?: string;
  net_pay?: string;
  status: string;
  status_display?: string;
  notes?: string;
}

export interface Payslip {
  id: string;
  record: string;
  employee: string;
  employee_name?: string;
  period: string;
  period_name?: string;
  reference: string;
  is_published: boolean;
  published_at?: string | null;
  snapshot?: Record<string, unknown>;
  created_at?: string;
}

/* ---------- Periods ---------- */
export async function listPayrollPeriods(params: { page?: number; status?: string } = {}) {
  const { data } = await api.get<Paginated<PayrollPeriod>>("/payroll-periods/", {
    params: { page_size: 50, ...params },
  });
  return data;
}

export async function getPayrollPeriod(id: string) {
  const { data } = await api.get<PayrollPeriod>(`/payroll-periods/${id}/`);
  return data;
}

export async function createPayrollPeriod(payload: {
  name: string;
  code: string;
  start_date: string;
  end_date: string;
  pay_date: string;
  notes?: string;
}) {
  const { data } = await api.post<PayrollPeriod>("/payroll-periods/", payload);
  return data;
}

export async function generatePayrollRecords(id: string) {
  const { data } = await api.post<{ period: string; records_created: number }>(
    `/payroll-periods/${id}/generate-records/`,
  );
  return data;
}

export async function approvePayrollPeriod(id: string) {
  const { data } = await api.post<PayrollPeriod>(`/payroll-periods/${id}/approve/`);
  return data;
}

export async function markPayrollPeriodPaid(id: string) {
  const { data } = await api.post<PayrollPeriod>(`/payroll-periods/${id}/mark-paid/`);
  return data;
}

export async function generatePayslips(id: string) {
  const { data } = await api.post<{ period: string; payslips_created: number }>(
    `/payroll-periods/${id}/generate-payslips/`,
  );
  return data;
}

export async function publishPayslips(id: string) {
  const { data } = await api.post<{ period: string; payslips_published: number }>(
    `/payroll-periods/${id}/publish-payslips/`,
  );
  return data;
}

export async function exportPayrollPeriod(
  id: string,
  fmt: "csv" | "xlsx" = "csv",
): Promise<{ blob: Blob; filename: string }> {
  // Use ?fmt= — `?format=` is reserved by DRF content negotiation.
  const response = await api.get(`/payroll-periods/${id}/export/`, {
    params: { fmt },
    responseType: "blob",
  });
  const disposition = response.headers["content-disposition"] as string | undefined;
  const match = disposition?.match(/filename\*?="?([^";]+)"?/);
  return {
    blob: response.data as Blob,
    filename: match?.[1] ?? `payroll_${id}.${fmt}`,
  };
}

/* ---------- Records ---------- */
export async function listPayrollRecords(
  params: { period?: string; employee?: string; status?: string; page?: number } = {},
) {
  const { data } = await api.get<Paginated<PayrollRecord>>("/payroll-records/", {
    params: { page_size: 200, ...params },
  });
  return data;
}

/* ---------- Payslips ---------- */
export async function listPayslips(params: { period?: string; employee?: string; page?: number } = {}) {
  const { data } = await api.get<Paginated<Payslip>>("/payslips/", {
    params: { page_size: 200, ...params },
  });
  return data;
}

export async function listMyPayslips() {
  const { data } = await api.get<Paginated<Payslip>>("/payslips/my-payslips/");
  return data.results;
}
