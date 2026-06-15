import { api } from "./client";

/* The reports module exposes a tenant-scoped summary used by the HR
   dashboard. The exact endpoint path may differ per backend release —
   `/reports/dashboard/` is our primary; consumers should tolerate a 404
   by rendering placeholders. */
export interface DashboardSummary {
  total_employees: number;
  active_employees: number;
  new_hires_this_month: number;
  exits_this_month: number;
  contracts_expiring_soon: number;
  probation_ending_soon: number;
  pending_leave_approvals: number;
  pending_education_claims: number;
  upcoming_birthdays: Array<{ id: string; name: string; date: string }>;
}

export async function getDashboardSummary(): Promise<DashboardSummary | null> {
  try {
    const { data } = await api.get<DashboardSummary>("/reports/dashboard/");
    return data;
  } catch {
    return null;
  }
}
