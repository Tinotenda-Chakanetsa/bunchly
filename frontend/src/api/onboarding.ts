import { api } from "./client";
import type { Paginated } from "./employees";

export interface OnboardingTask {
  id: string;
  programme: string;
  title: string;
  description: string;
  owner_role: string;
  owner_role_display?: string;
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  sequence: number;
  status: "pending" | "in_progress" | "complete" | "skipped" | "blocked" | string;
  status_display?: string;
  due_date?: string | null;
  completed_at?: string | null;
  completed_by?: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface OnboardingProgramme {
  id: string;
  employee: string;
  employee_name?: string;
  programme_type: string;
  programme_type_display?: string;
  template?: string | null;
  template_name?: string | null;
  status: string;
  status_display?: string;
  start_date: string;
  target_completion_date?: string | null;
  completed_at?: string | null;
  notes: string;
  tasks: OnboardingTask[];
  created_at: string;
  updated_at: string;
}

export interface ChecklistTemplate {
  id: string;
  name: string;
  programme_type: string;
  programme_type_display?: string;
  description: string;
  is_default: boolean;
  is_active: boolean;
  task_count?: number;
  created_at: string;
}

export async function listProgrammes(params: {
  programme_type?: string;
  employee?: string;
  page?: number;
} = {}) {
  const { data } = await api.get<Paginated<OnboardingProgramme>>(
    "/onboarding-programmes/",
    { params },
  );
  return data;
}

export async function getProgramme(id: string) {
  const { data } = await api.get<OnboardingProgramme>(
    `/onboarding-programmes/${id}/`,
  );
  return data;
}

export async function startProgramme(payload: {
  employee: string;
  programme_type: string;
  template?: string;
  start_date: string;
  target_completion_date?: string | null;
  notes?: string;
}) {
  const { data } = await api.post<OnboardingProgramme>(
    "/onboarding-programmes/",
    payload,
  );
  return data;
}

export async function listProgrammeTasks(programmeId: string) {
  const { data } = await api.get<Paginated<OnboardingTask>>("/onboarding-tasks/", {
    params: { programme: programmeId, page_size: 200 },
  });
  return data.results;
}

export async function addOnboardingTask(payload: {
  programme: string;
  title: string;
  description?: string;
  owner_role: string;
  sequence?: number;
  due_date?: string | null;
}) {
  const { data } = await api.post<OnboardingTask>("/onboarding-tasks/", payload);
  return data;
}

export async function setTaskStatus(
  id: string,
  status: "pending" | "in_progress" | "complete" | "skipped" | "blocked",
  notes = "",
) {
  const { data } = await api.post<OnboardingTask>(
    `/onboarding-tasks/${id}/set-status/`,
    { status, notes },
  );
  return data;
}

export async function listChecklistTemplates() {
  const { data } = await api.get<Paginated<ChecklistTemplate>>(
    "/checklist-templates/",
    { params: { page_size: 50 } },
  );
  return data.results;
}
