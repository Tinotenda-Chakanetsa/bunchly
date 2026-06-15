import { api } from "./client";
import type { Paginated } from "./employees";

export interface BenefitType {
  id: string;
  name: string;
  code: string;
  category: string;
  category_display?: string;
  description?: string;
  provider?: string;
  contribution_basis: string;
  employee_contribution?: string;
  employer_contribution?: string;
  is_taxable: boolean;
  requires_approval: boolean;
  covers_dependants: boolean;
  eligibility_min_months: number;
  eligible_employment_statuses?: string[];
  pay_component?: string;
  is_active: boolean;
  enrolment_count?: number;
  created_at?: string;
}

export interface EmployeeBenefit {
  id: string;
  employee: string;
  employee_name?: string;
  benefit_type: string;
  benefit_type_name?: string;
  status: string;
  status_display?: string;
  start_date?: string | null;
  end_date?: string | null;
  employee_contribution?: string;
  employer_contribution?: string;
  covered_dependants?: number;
  notes?: string;
  approved_at?: string | null;
  created_at?: string;
}

const PAGE = { params: { page_size: 200 } };

/* ---------- Benefit types ---------- */
export async function listBenefitTypes() {
  const { data } = await api.get<Paginated<BenefitType>>("/benefit-types/", PAGE);
  return data.results;
}

export async function createBenefitType(payload: Partial<BenefitType>) {
  const { data } = await api.post<BenefitType>("/benefit-types/", payload);
  return data;
}

export async function updateBenefitType(id: string, patch: Partial<BenefitType>) {
  const { data } = await api.patch<BenefitType>(`/benefit-types/${id}/`, patch);
  return data;
}

/* ---------- Enrolments ---------- */
export async function listEmployeeBenefits(
  params: { employee?: string; benefit_type?: string; status?: string; page?: number } = {},
) {
  const { data } = await api.get<Paginated<EmployeeBenefit>>("/employee-benefits/", {
    params: { page_size: 200, ...params },
  });
  return data;
}

export async function enrolBenefit(payload: {
  employee?: string;
  benefit_type: string;
  notes?: string;
}) {
  const { data } = await api.post<EmployeeBenefit>("/employee-benefits/", payload);
  return data;
}

export async function approveBenefitEnrolment(id: string) {
  const { data } = await api.post<EmployeeBenefit>(`/employee-benefits/${id}/approve/`);
  return data;
}

export async function declineBenefitEnrolment(id: string, note = "") {
  const { data } = await api.post<EmployeeBenefit>(`/employee-benefits/${id}/decline/`, {
    note,
  });
  return data;
}

export async function suspendBenefitEnrolment(id: string, note = "") {
  const { data } = await api.post<EmployeeBenefit>(`/employee-benefits/${id}/suspend/`, {
    note,
  });
  return data;
}

export async function terminateBenefitEnrolment(id: string, note = "") {
  const { data } = await api.post<EmployeeBenefit>(`/employee-benefits/${id}/terminate/`, {
    note,
  });
  return data;
}
