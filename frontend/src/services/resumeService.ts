import api from './api';
import type {
  Resume,
  ResumeUploadResponse,
  ResumeScoreResponse,
  ResumeGenerateRequest,
  ResumeListResponse,
} from '@/types/resume';

/** Upload a PDF or DOCX resume file. */
export async function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post<ResumeUploadResponse>('/resumes/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

/** List all uploaded and generated resumes. */
export async function listResumes(): Promise<ResumeListResponse> {
  const { data } = await api.get<ResumeListResponse>('/resumes/');
  return data;
}

/** Generate a job-tailored resume from a base resume. */
export async function generateResume(request: ResumeGenerateRequest): Promise<Resume> {
  const { data } = await api.post<Resume>('/resumes/generate', request);
  return data;
}

/** Score a resume's ATS compatibility against a specific job. */
export async function scoreResume(
  resumeId: string,
  jobId: string,
): Promise<ResumeScoreResponse> {
  const { data } = await api.post<ResumeScoreResponse>(`/resumes/${resumeId}/score`, {
    job_id: jobId,
  });
  return data;
}

/** Optimize a resume for ATS keyword matching. */
export async function optimizeResume(resumeId: string): Promise<Resume> {
  const { data } = await api.post<Resume>(`/resumes/${resumeId}/optimize`);
  return data;
}

/** Get the download URL for a resume file. */
export function getDownloadUrl(resumeId: string, format: 'pdf' | 'docx' = 'pdf'): string {
  const baseURL = api.defaults.baseURL ?? '/api/v1';
  return `${baseURL}/resumes/${resumeId}/download?format=${format}`;
}
