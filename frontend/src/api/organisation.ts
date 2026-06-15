import { api } from "./client";
import type { Paginated } from "./employees";

export interface Department {
  id: string;
  name: string;
  code?: string;
  description?: string;
  parent?: string | null;
  parent_name?: string | null;
  cost_centre?: string | null;
  cost_centre_name?: string | null;
  location?: string | null;
  location_name?: string | null;
  head?: string | null;
  head_name?: string | null;
  employee_count?: number;
  is_active?: boolean;
  created_at?: string;
}

export interface Team {
  id: string;
  name: string;
  code?: string;
  department: string;
  department_name?: string;
  description?: string;
  is_active?: boolean;
}

export interface Location {
  id: string;
  name: string;
  code?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  timezone?: string;
  is_active?: boolean;
}

export interface JobTitle {
  id: string;
  name: string;
  code?: string;
  description?: string;
  is_active?: boolean;
}

export interface Grade {
  id: string;
  name: string;
  code?: string;
  level?: number;
  description?: string;
  is_active?: boolean;
}

export interface CostCentre {
  id: string;
  name: string;
  code?: string;
  description?: string;
  is_active?: boolean;
}

export interface Position {
  id: string;
  name: string;
  job_title: string;
  job_title_name?: string;
  department: string;
  department_name?: string;
  grade?: string | null;
  grade_name?: string | null;
  location?: string | null;
  location_name?: string | null;
  reports_to?: string | null;
  headcount: number;
  is_vacant: boolean;
  is_active?: boolean;
}

const PAGE = { params: { page_size: 200 } };

/* ---------- Departments ---------- */
export async function listDepartments() {
  const { data } = await api.get<Paginated<Department>>("/organisation/departments/", PAGE);
  return data.results;
}
export async function createDepartment(payload: Partial<Department>) {
  const { data } = await api.post<Department>("/organisation/departments/", payload);
  return data;
}
export async function updateDepartment(id: string, patch: Partial<Department>) {
  const { data } = await api.patch<Department>(`/organisation/departments/${id}/`, patch);
  return data;
}
export async function deleteDepartment(id: string) {
  await api.delete(`/organisation/departments/${id}/`);
}

/* ---------- Teams ---------- */
export async function listTeams() {
  const { data } = await api.get<Paginated<Team>>("/organisation/teams/", PAGE);
  return data.results;
}
export async function createTeam(payload: Partial<Team>) {
  const { data } = await api.post<Team>("/organisation/teams/", payload);
  return data;
}

/* ---------- Locations ---------- */
export async function listLocations() {
  const { data } = await api.get<Paginated<Location>>("/organisation/locations/", PAGE);
  return data.results;
}
export async function createLocation(payload: Partial<Location>) {
  const { data } = await api.post<Location>("/organisation/locations/", payload);
  return data;
}

/* ---------- Job titles ---------- */
export async function listJobTitles() {
  const { data } = await api.get<Paginated<JobTitle>>("/organisation/job-titles/", PAGE);
  return data.results;
}
export async function createJobTitle(payload: Partial<JobTitle>) {
  const { data } = await api.post<JobTitle>("/organisation/job-titles/", payload);
  return data;
}

/* ---------- Grades / Cost centres / Positions ---------- */
export async function listGrades() {
  const { data } = await api.get<Paginated<Grade>>("/organisation/grades/", PAGE);
  return data.results;
}
export async function listCostCentres() {
  const { data } = await api.get<Paginated<CostCentre>>("/organisation/cost-centres/", PAGE);
  return data.results;
}
export async function listPositions() {
  const { data } = await api.get<Paginated<Position>>("/organisation/positions/", PAGE);
  return data.results;
}
