import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import ResumeCard from '@/components/resumes/ResumeCard';
import type { Resume } from '@/types/resume';

const resume = (o: Partial<Resume> = {}): Resume => ({
  id: 'r1', name: 'Alex Morgan — Senior PM', type: 'optimized', template_id: 'modern',
  base_resume_id: 'b1', job_id: null, has_pdf: true, has_docx: false, ats_score: 0.86,
  created_at: '2026-07-01T00:00:00Z', updated_at: '2026-07-01T00:00:00Z', ...o,
});

const noop = () => {};

describe('ResumeCard', () => {
  it('shows the name, type badge, and ATS (0–1 scaled to percent)', () => {
    render(<ResumeCard resume={resume()} selected={false} onSelect={noop} onOptimize={noop} onDownload={noop} optimizing={false} />);
    expect(screen.getByText('Alex Morgan — Senior PM')).toBeInTheDocument();
    expect(screen.getByText('Optimized')).toBeInTheDocument();
    expect(screen.getByText('86')).toBeInTheDocument();
  });

  it('fires select, optimize, and download callbacks', async () => {
    const onSelect = vi.fn();
    const onOptimize = vi.fn();
    const onDownload = vi.fn();
    render(<ResumeCard resume={resume()} selected={false} onSelect={onSelect} onOptimize={onOptimize} onDownload={onDownload} optimizing={false} />);

    await userEvent.click(screen.getByRole('button', { name: /select résumé/i }));
    expect(onSelect).toHaveBeenCalledOnce();

    await userEvent.click(screen.getByRole('button', { name: /^optimize$/i }));
    expect(onOptimize).toHaveBeenCalledOnce();

    await userEvent.click(screen.getByRole('button', { name: /^download$/i }));
    expect(onDownload).toHaveBeenCalledOnce();
    expect(onSelect).toHaveBeenCalledOnce(); // inner buttons don't bubble to select
  });
});
