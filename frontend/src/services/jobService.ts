import api from './api';
import type {
  Job,
  JobSearchRequest,
  JobListResponse,
  JobSearchResponse,
  JobAnalysisResponse,
  SearchStatusResponse,
} from '@/types/job';

/**
 * Board searches drive a real browser and the backend caps each one at
 * BROWSER__SEARCH_TIMEOUT_S (90s default), so outlast that instead of the 30s client default.
 */
const SEARCH_TIMEOUT_MS = 120_000;

/** Search for jobs across multiple platforms. */
export async function searchJobs(request: JobSearchRequest): Promise<JobSearchResponse> {
  const { data } = await api.post<JobSearchResponse>('/jobs/search', request, {
    timeout: SEARCH_TIMEOUT_MS,
  });
  return data;
}

/** Per-board status of a background search (404 once expired or when Redis is down). */
export async function getSearchStatus(searchId: string): Promise<SearchStatusResponse> {
  const { data } = await api.get<SearchStatusResponse>(`/jobs/search/${encodeURIComponent(searchId)}`);
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
export async function analyzeJob(jobId: string, resumeId?: string): Promise<JobAnalysisResponse> {
  const params: Record<string, string> = {};
  if (resumeId) {
    params['resume_id'] = resumeId;
  }
  const { data } = await api.post<JobAnalysisResponse>(
    `/jobs/${jobId}/analyze`,
    undefined,
    Object.keys(params).length > 0 ? { params } : undefined,
  );
  return data;
}
