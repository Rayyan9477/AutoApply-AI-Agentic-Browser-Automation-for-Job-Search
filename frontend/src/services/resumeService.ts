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

/**
 * Download a resume file. The endpoint streams a bearer-gated FileResponse, so a plain link
 * can't authenticate — fetch it through the api client (which attaches the token) as a blob
 * and hand it to the browser via a transient object URL.
 */
export async function downloadResumeFile(
  resumeId: string,
  format: 'pdf' | 'docx',
  name: string,
): Promise<void> {
  const { data } = await api.get<Blob>(`/resumes/${resumeId}/download`, {
    params: { format },
    responseType: 'blob',
  });
  const url = URL.createObjectURL(data);
  try {
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}
