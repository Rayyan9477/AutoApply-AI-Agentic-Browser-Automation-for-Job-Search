import type { PaginatedResponse } from './api';

export type ApplicationStatus =
  | 'queued'
  | 'pending_review'
  | 'approved'
  | 'applying'
  | 'applied'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'withdrawn'
  | 'failed'
  | 'simulated';

/**
 * A single job application record.
 * Corresponds to the backend `ApplicationResponse` Pydantic schema.
 */
export interface Application {
  id: string;
  job_id: string;
  job_title: string | null;
  company: string | null;
  resume_id: string | null;
  status: ApplicationStatus | string;
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
