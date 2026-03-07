import type { PaginatedResponse } from './api';

/**
 * A single job listing from any platform.
 * Corresponds to the backend `JobListingResponse` Pydantic schema.
 */
export interface Job {
  id: string;
  platform: string;
  platform_job_id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  description: string;
  salary_range: string | null;
  job_type: string | null;
  remote: boolean;
  posted_date: string | null;
  experience_level: string | null;
  match_score: number | null;
  skills_required: Record<string, unknown> | null;
  status: string;
  created_at: string;
  updated_at: string;
}

/** Alias matching the backend schema name `JobListingResponse`. */
export type JobListingResponse = Job;

/** Request body for multi-platform job search. */
export interface JobSearchRequest {
  query: string;
  location?: string;
  platforms?: string[];
  filters?: Record<string, unknown>;
  limit?: number;
}

/** Paginated list of job listings. */
export type JobListResponse = PaginatedResponse<Job>;

/** Response from the job analysis endpoint. */
export interface JobAnalysisResponse {
  job_id: string;
  match_score: number;
  skill_match: number;
  keyword_match: number;
  missing_skills: string[];
  suggestions: string[];
}
