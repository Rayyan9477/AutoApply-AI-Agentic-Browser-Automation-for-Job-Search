import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import ResumePreviewPanel from '@/components/resumes/ResumePreviewPanel';
import type { Resume, ResumeScoreResponse } from '@/types/resume';
import type { Job } from '@/types/job';

const resume = (o: Partial<Resume> = {}): Resume => ({
  id: 'r1', name: 'Alex Morgan — Base', type: 'base', template_id: 'modern',
  base_resume_id: null, job_id: null, has_pdf: true, has_docx: false, ats_score: 0.82,
  created_at: '2026-07-01T00:00:00Z', updated_at: '2026-07-01T00:00:00Z', ...o,
});

const jobs: Job[] = [{
  id: 'j1', platform: 'linkedin', platform_job_id: 'ln1', title: 'Senior PM', company: 'Northwind',
  location: 'Remote', url: 'https://x', description: '', salary_range: null, job_type: null,
  remote: true, posted_date: null, experience_level: null, match_score: 0.9, skills_required: null,
  status: 'new', created_at: '', updated_at: '',
}];

const score: ResumeScoreResponse = {
  resume_id: 'r1', job_id: 'j1', overall_score: 0.9, skill_score: 0.92, experience_score: 0.8,
  education_score: 0.7, keyword_score: 0.85, missing_skills: [], suggestions: [],
};

const noop = () => {};
const base = {
  resume: resume(), score: null as ResumeScoreResponse | null, scoring: false, jobs,
  targetJobId: '', onSelectJob: noop, onScore: noop, onDownload: (() => {}) as (f: 'pdf' | 'docx') => void,
};

describe('ResumePreviewPanel', () => {
  it('shows the selected résumé name and its base ATS', () => {
    render(<ResumePreviewPanel {...base} />);
    expect(screen.getByText('Alex Morgan — Base')).toBeInTheDocument();
    expect(screen.getByText('82')).toBeInTheDocument();
  });

  it('disables "Score vs job" until a job is chosen', () => {
    render(<ResumePreviewPanel {...base} targetJobId="" />);
    expect(screen.getByRole('button', { name: /score vs job/i })).toBeDisabled();
  });

  it('fires onScore when a job is chosen', async () => {
    const onScore = vi.fn();
    render(<ResumePreviewPanel {...base} targetJobId="j1" onScore={onScore} />);
    await userEvent.click(screen.getByRole('button', { name: /score vs job/i }));
    expect(onScore).toHaveBeenCalledOnce();
  });

  it('shows the sub-score breakdown after scoring', () => {
    render(<ResumePreviewPanel {...base} score={score} />);
    expect(screen.getByText(/skill/i)).toBeInTheDocument();
    expect(screen.getByText('90')).toBeInTheDocument(); // overall 0.9 → 90
  });

  it('downloads the PDF', async () => {
    const onDownload = vi.fn();
    render(<ResumePreviewPanel {...base} onDownload={onDownload} />);
    await userEvent.click(screen.getByRole('button', { name: /pdf/i }));
    expect(onDownload).toHaveBeenCalledWith('pdf');
  });
});
