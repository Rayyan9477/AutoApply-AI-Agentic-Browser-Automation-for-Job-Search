import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import JobDrawer from '@/components/jobs/JobDrawer';
import type { Job, JobAnalysisResponse } from '@/types/job';

const job = (o: Partial<Job> = {}): Job => ({
  id: 'j1', platform: 'linkedin', platform_job_id: 'ln1', title: 'Senior Product Manager',
  company: 'Northwind Labs', location: 'Remote', url: 'https://example.com/job',
  description: 'Own the roadmap.\n\nDrive outcomes.', salary_range: null, job_type: 'Full-time',
  remote: true, posted_date: null, experience_level: null, match_score: 0.9, skills_required: null,
  status: 'new', created_at: '', updated_at: '', ...o,
});

const analysis: JobAnalysisResponse = {
  job_id: 'j1', match_score: 0.88, skill_match: 0.92, keyword_match: 0.8,
  missing_skills: ['GraphQL', 'Kubernetes'], suggestions: ['Add GraphQL experience'],
};

const noop = () => {};

describe('JobDrawer', () => {
  it('shows the job header and analysis breakdown', () => {
    render(<JobDrawer job={job()} analysis={analysis} analyzing={false} baseResumeId="r1" generating={false} onClose={noop} onGenerate={noop} />);
    expect(screen.getByRole('dialog', { name: /job details/i })).toBeInTheDocument();
    expect(screen.getByText('Senior Product Manager')).toBeInTheDocument();
    expect(screen.getByText('88')).toBeInTheDocument(); // match_score 0.88 → 88 (0–1 scaled to percent)
    expect(screen.getByText('GraphQL')).toBeInTheDocument();
    expect(screen.getByText(/Add GraphQL experience/)).toBeInTheDocument();
  });

  it('disables "Generate tailored résumé" when there is no base résumé', () => {
    render(<JobDrawer job={job()} analysis={analysis} analyzing={false} baseResumeId={null} generating={false} onClose={noop} onGenerate={noop} />);
    expect(screen.getByRole('button', { name: /generate tailored résumé/i })).toBeDisabled();
  });

  it('fires onGenerate when a base résumé exists', async () => {
    const onGenerate = vi.fn();
    render(<JobDrawer job={job()} analysis={analysis} analyzing={false} baseResumeId="r1" generating={false} onClose={noop} onGenerate={onGenerate} />);
    await userEvent.click(screen.getByRole('button', { name: /generate tailored résumé/i }));
    expect(onGenerate).toHaveBeenCalledOnce();
  });

  it('links "View posting" to the job url', () => {
    render(<JobDrawer job={job()} analysis={null} analyzing={false} baseResumeId="r1" generating={false} onClose={noop} onGenerate={noop} />);
    expect(screen.getByRole('link', { name: /view posting/i })).toHaveAttribute('href', 'https://example.com/job');
  });
});
