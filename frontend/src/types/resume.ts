/**
 * A stored resume record.
 * Corresponds to the backend `ResumeResponse` Pydantic schema.
 */
export interface Resume {
  id: string;
  name: string;
  type: string;
  template_id: string;
  base_resume_id: string | null;
  job_id: string | null;
  file_path_pdf: string | null;
  file_path_docx: string | null;
  ats_score: number | null;
  created_at: string;
  updated_at: string;
}

/** Alias matching the backend schema name `ResumeResponse`. */
export type ResumeResponse = Resume;

/** Response after uploading a resume file. */
export interface ResumeUploadResponse {
  id: string;
  name: string;
  file_format: string;
  word_count: number;
  skills_detected: string[];
}

/** ATS score breakdown for a resume against a job. */
export interface ResumeScoreResponse {
  resume_id: string;
  job_id: string;
  overall_score: number;
  skill_score: number;
  experience_score: number;
  education_score: number;
  keyword_score: number;
  missing_skills: string[];
  suggestions: string[];
}

/** Request to score a resume against a job listing. */
export interface ResumeScoreRequest {
  job_id: string;
}

/** Request to generate a tailored resume. */
export interface ResumeGenerateRequest {
  base_resume_id: string;
  job_id: string;
  template_id?: string;
  output_formats?: string[];
}

/** Paginated list of resumes. */
export interface ResumeListResponse {
  items: Resume[];
  total: number;
}
