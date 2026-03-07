import type { PaginatedResponse } from './api';

/**
 * A single job application record.
 * Corresponds to the backend `ApplicationResponse` Pydantic schema.
 */
export interface Application {
  id: string;
  job_id: string;
  resume_id: string | null;
  status: string;
  apply_mode: string;
  ats_score: number | null;
  cover_letter_path: string | null;
  applied_at: string | null;
  response_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

/** Alias matching the backend schema name `ApplicationResponse`. */
export type ApplicationResponse = Application;

/** Request to create a single application. */
export interface ApplicationCreate {
  job_id: string;
  resume_id?: string | null;
  apply_mode?: string;
}

/** Request to create multiple applications at once. */
export interface ApplicationBatchCreate {
  job_ids: string[];
  resume_id?: string | null;
  apply_mode?: string;
}

/** Request to update an application's status. */
export interface ApplicationStatusUpdate {
  status: string;
  notes?: string | null;
}

/** Paginated list of applications. */
export type ApplicationListResponse = PaginatedResponse<Application>;
