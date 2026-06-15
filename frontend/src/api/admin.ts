import { api } from "./client";
import type { Paginated } from "./employees";

/* ================================================================ *
 * Imports — /imports/ (validate + commit two-step)
 * ================================================================ */

export interface ImportBatch {
  id: string;
  entity_type: string;
  entity_type_display?: string;
  status: string;
  status_display?: string;
  original_filename?: string;
  total_rows: number;
  valid_rows: number;
  error_rows: number;
  committed_rows: number;
  committed_at?: string | null;
  created_at: string;
  notes?: string;
  errors?: Array<{
    id: string;
    row_number: number;
    field?: string;
    error: string;
  }>;
}

export interface ImportEntity {
  key: string;
  label: string;
  columns: string[];
  required: string[];
  /** Per-column help strings, keyed by column name. Backend ships
   *  `template_help` here, e.g. {"employee_number": "Required. Unique per tenant."}. */
  help?: Record<string, string>;
}

export async function listImportEntityTypes() {
  const { data } = await api.get<{ entities: ImportEntity[] }>(
    "/imports/entity-types/",
  );
  return data.entities;
}

export async function listImportBatches(params: { page?: number } = {}) {
  const { data } = await api.get<Paginated<ImportBatch>>("/imports/", {
    params: { page_size: 50, ...params },
  });
  return data;
}

export async function getImportBatch(id: string) {
  const { data } = await api.get<ImportBatch>(`/imports/${id}/`);
  return data;
}

export async function validateImport(payload: { entity_type: string; file: File }) {
  const form = new FormData();
  form.append("entity_type", payload.entity_type);
  form.append("file", payload.file);
  const { data } = await api.post<ImportBatch>("/imports/validate/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function commitImport(id: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<ImportBatch>(`/imports/${id}/commit/`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function downloadImportTemplate(entity_type: string) {
  const response = await api.get(`/imports/template/`, {
    params: { entity_type },
    responseType: "blob",
  });
  return response.data as Blob;
}

/* ================================================================ *
 * Reports — /reports/ (catalogue + run + export) + /saved-reports/
 * ================================================================ */

export interface ReportCatalogueEntry {
  key: string;
  label: string;
  description?: string;
}

export interface SavedReport {
  id: string;
  name: string;
  report_key: string;
  filters?: Record<string, unknown>;
  is_favourite?: boolean;
  created_at?: string;
}

export async function listReportCatalogue() {
  const { data } = await api.get<{ reports: ReportCatalogueEntry[] }>(
    "/reports/catalogue/",
  );
  return data.reports;
}

export async function exportReport(
  key: string,
  fmt: "csv" | "xlsx" = "csv",
  filters: Record<string, string | undefined> = {},
): Promise<{ blob: Blob; filename: string }> {
  // Backend uses ?fmt= (not ?format=) — DRF reserves `format` for
  // content negotiation and 404s when the value isn't a registered
  // renderer.
  const response = await api.get(`/reports/export/`, {
    params: { report: key, fmt, ...filters },
    responseType: "blob",
  });
  const disposition = response.headers["content-disposition"] as string | undefined;
  const match = disposition?.match(/filename\*?="?([^";]+)"?/);
  return {
    blob: response.data as Blob,
    filename: match?.[1] ?? `${key}.${fmt}`,
  };
}

export async function runReport(
  key: string,
  filters: Record<string, string | undefined> = {},
) {
  const { data } = await api.get<{
    report: string;
    generated_at: string;
    columns: Array<{ key: string; label?: string }>;
    rows: Array<Record<string, unknown>>;
    summary?: Record<string, unknown>;
    row_count: number;
  }>("/reports/run/", { params: { report: key, ...filters } });
  return data;
}

export async function listSavedReports() {
  const { data } = await api.get<Paginated<SavedReport>>("/saved-reports/", {
    params: { page_size: 100 },
  });
  return data.results;
}

export async function createSavedReport(payload: {
  name: string;
  report_key: string;
  filters?: Record<string, unknown>;
  is_favourite?: boolean;
}) {
  const { data } = await api.post<SavedReport>("/saved-reports/", payload);
  return data;
}

export async function updateSavedReport(id: string, patch: Partial<SavedReport>) {
  const { data } = await api.patch<SavedReport>(`/saved-reports/${id}/`, patch);
  return data;
}

export async function deleteSavedReport(id: string) {
  await api.delete(`/saved-reports/${id}/`);
}

/* ================================================================ *
 * Tenant + Tenant Settings — /tenants/current/ + .../settings/
 * ================================================================ */

export interface TenantSettings {
  id: string;
  timezone?: string;
  locale?: string;
  primary_color?: string;
  logo?: string | null;
  email_sender_name?: string;
  email_reply_to?: string;
  notification_recipients?: string[];
  max_upload_size_mb?: number;
  allowed_upload_extensions?: string[];
  module_flags?: Record<string, unknown>;
  data_retention_days?: number;
  updated_at?: string;
}

export interface CurrentTenant {
  id: string;
  name: string;
  slug: string;
  legal_name?: string;
  industry?: string;
  country?: string;
  is_active: boolean;
  onboarded_at?: string;
  domains?: Array<{ id: string; domain: string; is_primary: boolean }>;
  settings?: TenantSettings;
}

export async function getCurrentTenant() {
  const { data } = await api.get<Paginated<CurrentTenant> | CurrentTenant>(
    "/tenants/current/",
  );
  // ViewSet.list returns a single object via Response(...) — guard either shape.
  if ((data as Paginated<CurrentTenant>).results) {
    return (data as Paginated<CurrentTenant>).results[0];
  }
  return data as CurrentTenant;
}

export async function getTenantSettings() {
  const { data } = await api.get<TenantSettings>("/tenants/current/settings/");
  return data;
}

export async function updateTenantSettings(patch: Partial<TenantSettings>) {
  const { data } = await api.patch<TenantSettings>(
    "/tenants/current/settings/",
    patch,
  );
  return data;
}
