import { http, HttpResponse } from 'msw';

/** Sample job listing used across tests. */
const sampleJob = {
  id: 'job-1',
  platform: 'linkedin',
  platform_job_id: 'ln-12345',
  title: 'Senior Frontend Engineer',
  company: 'Acme Corp',
  location: 'San Francisco, CA',
  url: 'https://linkedin.com/jobs/12345',
  description: 'We are looking for a senior frontend engineer.',
  salary_range: '$150k - $200k',
  job_type: 'Full-time',
  remote: true,
  posted_date: '2026-03-10',
  experience_level: 'Senior',
  match_score: 0.85,
  skills_required: { react: true, typescript: true },
  status: 'new',
  created_at: '2026-03-10T12:00:00Z',
  updated_at: '2026-03-10T12:00:00Z',
};

const sampleJob2 = {
  ...sampleJob,
  id: 'job-2',
  platform_job_id: 'ln-67890',
  title: 'Backend Developer',
  company: 'Tech Inc',
  location: 'Remote',
  match_score: 0.62,
  remote: false,
  salary_range: null,
  job_type: null,
};

/** MSW v2 request handlers for all API endpoints. */
export const handlers = [
  // Jobs
  http.get('/api/v1/jobs/', () => {
    return HttpResponse.json({
      items: [sampleJob, sampleJob2],
      total: 2,
      page: 1,
      page_size: 20,
      has_next: false,
    });
  }),

  http.post('/api/v1/jobs/search', () => {
    return HttpResponse.json({
      items: [sampleJob],
      total: 1,
      page: 1,
      page_size: 20,
      has_next: false,
    });
  }),

  http.get('/api/v1/jobs/:jobId', ({ params }) => {
    if (params['jobId'] === 'job-1') {
      return HttpResponse.json(sampleJob);
    }
    return new HttpResponse(null, { status: 404 });
  }),

  http.post('/api/v1/jobs/:jobId/analyze', () => {
    return HttpResponse.json({
      job_id: 'job-1',
      match_score: 0.85,
      skill_match: 0.9,
      keyword_match: 0.8,
      missing_skills: ['GraphQL'],
      suggestions: ['Add GraphQL experience to resume'],
    });
  }),

  http.delete('/api/v1/jobs/:jobId', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Resumes
  http.get('/api/v1/resumes/', () => {
    return HttpResponse.json({
      items: [
        {
          id: 'resume-1',
          filename: 'my_resume.pdf',
          template: 'modern',
          created_at: '2026-03-01T00:00:00Z',
          updated_at: '2026-03-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      has_next: false,
    });
  }),

  http.post('/api/v1/resumes/upload', () => {
    return HttpResponse.json({
      id: 'resume-2',
      filename: 'uploaded_resume.pdf',
      status: 'uploaded',
    });
  }),

  http.post('/api/v1/resumes/generate', () => {
    return HttpResponse.json({
      id: 'resume-3',
      filename: 'generated_resume.pdf',
      template: 'modern',
      created_at: '2026-03-15T00:00:00Z',
      updated_at: '2026-03-15T00:00:00Z',
    });
  }),

  http.post('/api/v1/resumes/:resumeId/score', () => {
    return HttpResponse.json({
      resume_id: 'resume-1',
      job_id: 'job-1',
      score: 78,
      suggestions: ['Add more keywords'],
    });
  }),

  http.post('/api/v1/resumes/:resumeId/optimize', () => {
    return HttpResponse.json({
      id: 'resume-1',
      filename: 'optimized_resume.pdf',
      template: 'modern',
      created_at: '2026-03-01T00:00:00Z',
      updated_at: '2026-03-15T00:00:00Z',
    });
  }),

  // Applications
  http.get('/api/v1/applications/', () => {
    return HttpResponse.json({
      items: [
        {
          id: 'app-1',
          job_id: 'job-1',
          resume_id: 'resume-1',
          status: 'pending',
          created_at: '2026-03-12T00:00:00Z',
          updated_at: '2026-03-12T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      has_next: false,
    });
  }),

  http.post('/api/v1/applications/', () => {
    return HttpResponse.json({
      id: 'app-2',
      job_id: 'job-1',
      resume_id: 'resume-1',
      status: 'pending',
      created_at: '2026-03-15T00:00:00Z',
      updated_at: '2026-03-15T00:00:00Z',
    });
  }),

  http.post('/api/v1/applications/batch', () => {
    return HttpResponse.json([
      {
        id: 'app-3',
        job_id: 'job-1',
        resume_id: 'resume-1',
        status: 'pending',
        created_at: '2026-03-15T00:00:00Z',
        updated_at: '2026-03-15T00:00:00Z',
      },
    ]);
  }),

  http.get('/api/v1/applications/:appId', () => {
    return HttpResponse.json({
      id: 'app-1',
      job_id: 'job-1',
      resume_id: 'resume-1',
      status: 'pending',
      created_at: '2026-03-12T00:00:00Z',
      updated_at: '2026-03-12T00:00:00Z',
    });
  }),

  http.put('/api/v1/applications/:appId/approve', () => {
    return HttpResponse.json({
      id: 'app-1',
      job_id: 'job-1',
      resume_id: 'resume-1',
      status: 'approved',
      created_at: '2026-03-12T00:00:00Z',
      updated_at: '2026-03-15T00:00:00Z',
    });
  }),

  http.put('/api/v1/applications/:appId/status', () => {
    return HttpResponse.json({
      id: 'app-1',
      job_id: 'job-1',
      resume_id: 'resume-1',
      status: 'submitted',
      created_at: '2026-03-12T00:00:00Z',
      updated_at: '2026-03-15T00:00:00Z',
    });
  }),

  // Analytics
  http.get('/api/v1/analytics/dashboard', () => {
    return HttpResponse.json({
      total_jobs: 150,
      total_applications: 45,
      interviews_scheduled: 5,
      avg_match_score: 0.72,
    });
  }),

  http.get('/api/v1/analytics/funnel', () => {
    return HttpResponse.json([
      { stage: 'Applied', count: 45 },
      { stage: 'Screening', count: 20 },
      { stage: 'Interview', count: 5 },
      { stage: 'Offer', count: 1 },
    ]);
  }),

  http.get('/api/v1/analytics/ats-scores', () => {
    return HttpResponse.json([
      { range: '0-25', count: 5 },
      { range: '26-50', count: 15 },
      { range: '51-75', count: 20 },
      { range: '76-100', count: 10 },
    ]);
  }),

  http.get('/api/v1/analytics/llm-usage', () => {
    return HttpResponse.json([
      { provider: 'openai', tokens_used: 50000, cost: 2.5 },
      { provider: 'anthropic', tokens_used: 30000, cost: 1.8 },
    ]);
  }),

  http.get('/api/v1/analytics/timeline', () => {
    return HttpResponse.json([
      { date: '2026-03-10', applications: 5, jobs_found: 20 },
      { date: '2026-03-11', applications: 3, jobs_found: 15 },
    ]);
  }),

  // Settings
  http.get('/api/v1/settings/', () => {
    return HttpResponse.json({
      id: 'settings-1',
      default_template: 'modern',
      auto_apply: false,
      platforms: ['linkedin', 'indeed'],
      llm_provider: 'openai',
    });
  }),

  http.put('/api/v1/settings/', () => {
    return HttpResponse.json({
      id: 'settings-1',
      default_template: 'modern',
      auto_apply: true,
      platforms: ['linkedin', 'indeed'],
      llm_provider: 'openai',
    });
  }),

  http.get('/api/v1/settings/llm-providers', () => {
    return HttpResponse.json([
      { provider: 'openai', status: 'active', model: 'gpt-4' },
      { provider: 'anthropic', status: 'active', model: 'claude-3' },
    ]);
  }),
];
