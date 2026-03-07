import api from './api';
import type { Job, JobSearchRequest, JobListResponse, JobAnalysisResponse } from '@/types/job';

/** Search for jobs across multiple platforms. */
export async function searchJobs(request: JobSearchRequest): Promise<JobListResponse> {
  const { data } = await api.post<JobListResponse>('/jobs/search', request);
  return data;
}

/** List stored jobs with pagination and optional status filter. */
export async function listJobs(
  page = 1,
  pageSize = 20,
  status?: string,
): Promise<JobListResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (status) params['status'] = status;
  const { data } = await api.get<JobListResponse>('/jobs/', { params });
  return data;
}

/** Get a single job by ID. */
export async function getJob(jobId: string): Promise<Job> {
  const { data } = await api.get<Job>(`/jobs/${jobId}`);
  return data;
}

/** Analyze how well the candidate matches a job listing. */
export async function analyzeJob(jobId: string): Promise<JobAnalysisResponse> {
  const { data } = await api.post<JobAnalysisResponse>(`/jobs/${jobId}/analyze`);
  return data;
}

/** Delete a job listing and its associated applications. */
export async function deleteJob(jobId: string): Promise<void> {
  await api.delete(`/jobs/${jobId}`);
}
