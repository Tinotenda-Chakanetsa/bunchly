import { api } from "./client";

export interface EmployeeListItem {
  id: string;
  employee_code: string;
  employee_number?: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  work_email?: string;
  job_title_name?: string;
  department_name?: string;
  line_manager_name?: string | null;
  employment_status: string;
  employment_type: string;
  start_date?: string;
  contract_end_date?: string | null;
  probation_end_date?: string | null;
  work_location_name?: string | null;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface EmployeeDetail extends EmployeeListItem {
  preferred_name?: string;
  gender?: string;
  date_of_birth?: string;
  marital_status?: string;
  national_id?: string | null;
  passport_number?: string | null;
  personal_email?: string;
  phone?: string;
  alternate_phone?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  line_manager?: string | null;
  line_manager_name?: string;
  department?: string | null;
  job_title?: string | null;
  position?: string | null;
  position_name?: string;
  grade?: string | null;
  grade_name?: string;
  cost_centre?: string | null;
  cost_centre_name?: string;
  work_location?: string | null;
  confirmation_date?: string | null;
  retirement_date?: string | null;
  current_salary?: string | null;
  salary_currency?: string;
  bank_name?: string | null;
  bank_account_number?: string | null;
  bank_branch_code?: string | null;
  contracts?: EmploymentContract[];
}

export interface EmploymentContract {
  id: string;
  employee: string;
  contract_type: string;
  start_date: string;
  end_date?: string | null;
  signed_date?: string | null;
  base_salary?: string;
  currency?: string;
  generated_document?: string | null;
  status?: string;
}

export async function listEmployees(params: { search?: string; page?: number } = {}) {
  const { data } = await api.get<Paginated<EmployeeListItem>>("/employees/", { params });
  return data;
}

export async function getEmployee(id: string) {
  const { data } = await api.get<EmployeeDetail>(`/employees/${id}/`);
  return data;
}

export async function getMyEmployee() {
  const { data } = await api.get<EmployeeDetail>("/employees/me/");
  return data;
}

export async function createEmployee(payload: {
  first_name: string;
  last_name: string;
  employee_number: string;
  work_email?: string;
  personal_email?: string;
  department?: string;
  job_title?: string;
  line_manager?: string;
  employment_type: string;
  start_date: string;
}) {
  const { data } = await api.post<EmployeeDetail>("/employees/", payload);
  return data;
}

export async function updateEmployee(id: string, patch: Record<string, unknown>) {
  const { data } = await api.patch<EmployeeDetail>(`/employees/${id}/`, patch);
  return data;
}

export async function listEmployeeContracts(employeeId: string) {
  const { data } = await api.get<Paginated<EmploymentContract>>("/contracts/", {
    params: { employee: employeeId },
  });
  return data;
}

/* ---------- Contract generation + templates ---------- */

export interface ContractTemplate {
  id: string;
  name: string;
  code: string;
  description?: string;
  template_file?: string;
  discovered_placeholders: string[];
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ContractTemplateTokens {
  /** Placeholders the system fills automatically from tenant/employee/contract context. */
  auto: string[];
  /** Placeholders HR must enter at generation time. */
  manual: string[];
  /** Every unique token discovered when the template was uploaded. */
  all: string[];
}

export interface TemplatePreview {
  template_name: string;
  tokens: string[];
  values: Record<string, string>;
}

export async function listContractTemplates() {
  const { data } = await api.get<Paginated<ContractTemplate>>(
    "/contract-templates/",
    { params: { page_size: 100 } },
  );
  return data.results;
}

export async function uploadContractTemplate(payload: {
  name: string;
  code: string;
  description?: string;
  file: File;
  is_default?: boolean;
}): Promise<ContractTemplate> {
  const form = new FormData();
  form.append("name", payload.name);
  form.append("code", payload.code);
  if (payload.description) form.append("description", payload.description);
  form.append("template_file", payload.file);
  form.append("is_default", String(Boolean(payload.is_default)));
  // DRF coerces missing-multipart boolean to False; send is_active explicitly.
  form.append("is_active", "true");
  const { data } = await api.post<ContractTemplate>(
    "/contract-templates/",
    form,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return data;
}

export async function deleteContractTemplate(id: string): Promise<void> {
  await api.delete(`/contract-templates/${id}/`);
}

export async function updateContractTemplate(
  id: string,
  patch: Partial<ContractTemplate>,
): Promise<ContractTemplate> {
  const { data } = await api.patch<ContractTemplate>(
    `/contract-templates/${id}/`,
    patch,
  );
  return data;
}

export async function getContractTemplateTokens(templateId: string) {
  const { data } = await api.get<ContractTemplateTokens>(
    `/contract-templates/${templateId}/tokens/`,
  );
  return data;
}

export async function previewContractTemplate(
  templateId: string,
  params: {
    employee: string;
    contract_type?: string;
    start_date?: string;
    end_date?: string;
    job_title?: string;
  },
): Promise<TemplatePreview> {
  const { data } = await api.get<TemplatePreview>(
    `/contract-templates/${templateId}/preview/`,
    { params },
  );
  return data;
}

export async function getPlaceholderCatalogue(): Promise<string[]> {
  const { data } = await api.get<{ placeholders: string[] }>(
    "/contract-templates/placeholders/",
  );
  return data.placeholders;
}

export interface CreateContractInput {
  employee: string;
  contract_type: string;
  start_date: string;
  end_date?: string | null;
  signed_date?: string | null;
  reference?: string;
  job_title?: string;
  notes?: string;
  status?: string;
}

export async function createContract(payload: CreateContractInput) {
  const { data } = await api.post<EmploymentContract>("/contracts/", payload);
  return data;
}

/**
 * Generate the contract as a .docx file. The backend renders the
 * tenant's mail-merge template (or built-in fallback) and streams the
 * file back. Overrides carry both template_id (if any) and manual
 * placeholder values (e.g. ``witness_name``).
 */
export async function generateContractDocument(
  contractId: string,
  overrides: Record<string, unknown> = {},
): Promise<{ blob: Blob; filename: string }> {
  const response = await api.post(
    `/contracts/${contractId}/generate/`,
    overrides,
    { responseType: "blob" },
  );
  const disposition = response.headers["content-disposition"] as
    | string
    | undefined;
  const match = disposition?.match(/filename\*?="?([^";]+)"?/);
  return {
    blob: response.data as Blob,
    filename: match?.[1] ?? `contract-${contractId}.docx`,
  };
}
