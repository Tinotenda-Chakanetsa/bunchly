import { api } from "./client";
import type { Paginated } from "./employees";

export interface DocumentCategory {
  id: string;
  name: string;
  code: string;
  description?: string;
  is_required: boolean;
  requires_approval: boolean;
  is_sensitive: boolean;
  tracks_expiry: boolean;
  allowed_extensions: string;
  max_file_size_mb: number;
  is_active: boolean;
  document_count?: number;
}

export interface DocumentVersion {
  id: string;
  version_number: number;
  file_url?: string | null;
  original_filename: string;
  file_size: number;
  content_type: string;
  is_current: boolean;
  notes?: string;
  uploaded_by_name?: string | null;
  created_at: string;
}

export interface DocumentRecord {
  id: string;
  employee?: string;
  employee_name?: string;
  category: string;
  category_name?: string;
  category_code?: string;
  title: string;
  description?: string;
  status: string;
  status_display?: string;
  is_confidential: boolean;
  expiry_date?: string | null;
  current_version?: DocumentVersion | null;
  version_count?: number;
  created_at: string;
}

export async function listDocuments(
  params: { status?: string; employee?: string; category?: string; page?: number; page_size?: number } = {},
) {
  const { data } = await api.get<Paginated<DocumentRecord>>("/documents/", {
    params,
  });
  return data;
}

export async function listDocumentCategories() {
  const { data } = await api.get<Paginated<DocumentCategory>>(
    "/document-categories/",
    { params: { page_size: 100 } },
  );
  return data.results;
}

export async function uploadDocument(payload: {
  employee: string;
  category: string;
  title: string;
  description?: string;
  is_confidential?: boolean;
  file: File;
}) {
  const form = new FormData();
  form.append("employee", payload.employee);
  form.append("category", payload.category);
  form.append("title", payload.title);
  if (payload.description) form.append("description", payload.description);
  form.append("is_confidential", String(Boolean(payload.is_confidential)));
  form.append("file", payload.file);
  const { data } = await api.post<DocumentRecord>("/documents/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function verifyDocument(id: string, note = "") {
  // Backend's action is named `approve` (POST /documents/:id/approve/).
  const { data } = await api.post<DocumentRecord>(`/documents/${id}/approve/`, {
    note,
  });
  return data;
}

export async function rejectDocument(id: string, note = "") {
  const { data } = await api.post<DocumentRecord>(`/documents/${id}/reject/`, {
    note,
  });
  return data;
}
