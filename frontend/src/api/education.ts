import { api } from "./client";
import type { Paginated } from "./employees";

export interface Dependant {
  id: string;
  employee: string;
  employee_name?: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  relationship: string;
  education_level: string;
  institution_name: string;
  student_number: string;
  is_eligible: boolean;
}

export interface EducationClaim {
  id: string;
  employee: string;
  employee_name?: string;
  dependant: string;
  dependant_name?: string;
  education_level: string;
  academic_period: string;
  institution_name: string;
  amount_claimed: string;
  amount_approved?: string;
  amount_paid?: string;
  status: string;
  status_display?: string;
  submitted_at?: string;
  approved_at?: string;
  paid_at?: string;
  payment_reference?: string;
  notes?: string;
  created_at: string;
}

export async function listEducationClaims(params: {
  status?: string;
  employee?: string;
  page?: number;
} = {}) {
  const { data } = await api.get<Paginated<EducationClaim>>(
    "/education-claims/",
    { params },
  );
  return data;
}

export async function listPendingHRClaims() {
  const { data } = await api.get<Paginated<EducationClaim>>(
    "/education-claims/pending-hr/",
  );
  return data.results;
}

export async function listPendingPaymentClaims() {
  const { data } = await api.get<Paginated<EducationClaim>>(
    "/education-claims/pending-payment/",
  );
  return data.results;
}

export async function listMyClaims() {
  const { data } = await api.get<Paginated<EducationClaim>>(
    "/education-claims/my-claims/",
  );
  return data.results;
}

export async function submitEducationClaim(payload: {
  dependant: string;
  education_level: string;
  academic_period: string;
  institution_name: string;
  amount_claimed: number;
  notes?: string;
}) {
  const { data } = await api.post<EducationClaim>(
    "/education-claims/",
    payload,
  );
  if (data.status === "draft") {
    const { data: submitted } = await api.post<EducationClaim>(
      `/education-claims/${data.id}/submit/`,
    );
    return submitted;
  }
  return data;
}

export async function hrApproveClaim(
  id: string,
  amount_approved: number,
  comment = "",
) {
  const { data } = await api.post<EducationClaim>(
    `/education-claims/${id}/hr-approve/`,
    { amount_approved, comment },
  );
  return data;
}

export async function hrRejectClaim(id: string, reason: string) {
  const { data } = await api.post<EducationClaim>(
    `/education-claims/${id}/hr-reject/`,
    { reason },
  );
  return data;
}

export async function markClaimPaid(payload: {
  id: string;
  amount_paid: number;
  payment_reference: string;
}) {
  const { data } = await api.post<EducationClaim>(
    `/education-claims/${payload.id}/mark-paid/`,
    {
      amount_paid: payload.amount_paid,
      payment_reference: payload.payment_reference,
    },
  );
  return data;
}

export async function listDependants(employeeId?: string) {
  const { data } = await api.get<Paginated<Dependant>>("/dependants/", {
    params: employeeId ? { employee: employeeId } : {},
  });
  return data.results;
}
