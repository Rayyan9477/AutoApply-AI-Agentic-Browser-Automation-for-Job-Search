import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as resumeService from '@/services/resumeService';
import type { ResumeGenerateRequest } from '@/types/resume';

const RESUMES_KEY = ['resumes'] as const;

/** Fetch all resumes. */
export function useResumes() {
  return useQuery({
    queryKey: [...RESUMES_KEY, 'list'],
    queryFn: () => resumeService.listResumes(),
  });
}

/** Upload a resume file. */
export function useUploadResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => resumeService.uploadResume(file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: RESUMES_KEY });
    },
  });
}

/** Generate a tailored resume. */
export function useGenerateResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: ResumeGenerateRequest) => resumeService.generateResume(request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: RESUMES_KEY });
    },
  });
}

/** Score a resume against a job. */
export function useScoreResume() {
  return useMutation({
    mutationFn: ({ resumeId, jobId }: { resumeId: string; jobId: string }) =>
      resumeService.scoreResume(resumeId, jobId),
  });
}

/** Optimize a resume for ATS. */
export function useOptimizeResume() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (resumeId: string) => resumeService.optimizeResume(resumeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: RESUMES_KEY });
    },
  });
}
