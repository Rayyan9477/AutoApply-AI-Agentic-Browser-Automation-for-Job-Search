import api from './api';
import type {
  Application,
  ApplicationCreate,
  ApplicationBatchCreate,
  ApplicationStatusUpdate,
  ApplicationListResponse,
} from '@/types/application';

/** Create a single job application. */
export async function createApplication(
  data: ApplicationCreate,
): Promise<Application> {
  const { data: result } = await api.post<Application>('/applications/', data);
  return result;
}

/** Create multiple job applications at once. */
export async function batchCreateApplications(
  data: ApplicationBatchCreate,
): Promise<Application[]> {
  const { data: result } = await api.post<Application[]>('/applications/batch', data);
  return result;
}

/** List applications with pagination and optional status filter. */
export async function listApplications(
  page = 1,
  pageSize = 20,
  status?: string,
): Promise<ApplicationListResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (status) params['status'] = status;
  const { data } = await api.get<ApplicationListResponse>('/applications/', { params });
  return data;
}

/** Get a single application by ID. */
export async function getApplication(appId: string): Promise<Application> {
  const { data } = await api.get<Application>(`/applications/${appId}`);
  return data;
}

/** Approve a pending application for automated submission. */
export async function approveApplication(appId: string): Promise<Application> {
  const { data } = await api.put<Application>(`/applications/${appId}/approve`);
  return data;
}

/** Update an application's status. */
export async function updateApplicationStatus(
  appId: string,
  update: ApplicationStatusUpdate,
): Promise<Application> {
  const { data } = await api.put<Application>(`/applications/${appId}/status`, update);
  return data;
}
