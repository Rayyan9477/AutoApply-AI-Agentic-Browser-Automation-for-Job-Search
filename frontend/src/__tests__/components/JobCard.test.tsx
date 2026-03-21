import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import JobCard from '@/components/jobs/JobCard';
import type { Job } from '@/types/job';

/** Factory for creating a Job object with sensible defaults. */
function makeJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 'job-1',
    platform: 'linkedin',
    platform_job_id: 'ln-12345',
    title: 'Senior Frontend Engineer',
    company: 'Acme Corp',
    location: 'San Francisco, CA',
    url: 'https://linkedin.com/jobs/12345',
    description: 'Build amazing UIs.',
    salary_range: '$150k - $200k',
    job_type: 'Full-time',
    remote: true,
    posted_date: '2026-03-10',
    experience_level: 'Senior',
    match_score: 0.85,
    skills_required: { react: true },
    status: 'new',
    created_at: '2026-03-10T12:00:00Z',
    updated_at: '2026-03-10T12:00:00Z',
    ...overrides,
  };
}

describe('JobCard', () => {
  it('renders the job title', () => {
    const job = makeJob();
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.getByText('Senior Frontend Engineer')).toBeInTheDocument();
  });

  it('renders the company name', () => {
    const job = makeJob();
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
  });

  it('renders the location', () => {
    const job = makeJob();
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.getByText('San Francisco, CA')).toBeInTheDocument();
  });

  it('shows "Remote" when location is empty', () => {
    const job = makeJob({ location: '', remote: false });
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.getByText('Remote')).toBeInTheDocument();
  });

  it('renders the platform chip', () => {
    const job = makeJob({ platform: 'indeed' });
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.getByText('indeed')).toBeInTheDocument();
  });

  it('renders a Remote chip when job.remote is true', () => {
    const job = makeJob({ remote: true });
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    // There will be two "Remote" occurrences - one in the location area and one as a chip.
    // The chip has label "Remote" and the location shows location text.
    const remoteChips = screen.getAllByText('Remote');
    expect(remoteChips.length).toBeGreaterThanOrEqual(1);
  });

  it('does not render Remote chip when job.remote is false', () => {
    const job = makeJob({ remote: false, location: 'NYC' });
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    // "Remote" should not appear at all since remote=false and location is set
    expect(screen.queryByText('Remote')).not.toBeInTheDocument();
  });

  it('renders job_type chip when provided', () => {
    const job = makeJob({ job_type: 'Full-time' });
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.getByText('Full-time')).toBeInTheDocument();
  });

  it('does not render job_type chip when null', () => {
    const job = makeJob({ job_type: null });
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.queryByText('Full-time')).not.toBeInTheDocument();
  });

  it('renders salary_range chip when provided', () => {
    const job = makeJob({ salary_range: '$100k - $150k' });
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.getByText('$100k - $150k')).toBeInTheDocument();
  });

  it('does not render salary_range chip when null', () => {
    const job = makeJob({ salary_range: null });
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.queryByText('$150k - $200k')).not.toBeInTheDocument();
  });

  it('renders match score as percentage when match_score is set', () => {
    const job = makeJob({ match_score: 0.85 });
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('rounds match score correctly', () => {
    const job = makeJob({ match_score: 0.678 });
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.getByText('68%')).toBeInTheDocument();
  });

  it('does not render match score chip when match_score is null', () => {
    const job = makeJob({ match_score: null });
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.queryByText('%')).not.toBeInTheDocument();
  });

  it('renders View Details button', () => {
    const job = makeJob();
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'View Details' })).toBeInTheDocument();
  });

  it('calls onViewDetails with job id when View Details is clicked', async () => {
    const user = userEvent.setup();
    const onViewDetails = vi.fn();
    const job = makeJob({ id: 'job-42' });

    render(<JobCard job={job} onViewDetails={onViewDetails} />);
    await user.click(screen.getByRole('button', { name: 'View Details' }));

    expect(onViewDetails).toHaveBeenCalledOnce();
    expect(onViewDetails).toHaveBeenCalledWith('job-42');
  });

  it('renders Apply button when onApply is provided', () => {
    const job = makeJob();
    render(<JobCard job={job} onViewDetails={vi.fn()} onApply={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Apply' })).toBeInTheDocument();
  });

  it('does not render Apply button when onApply is not provided', () => {
    const job = makeJob();
    render(<JobCard job={job} onViewDetails={vi.fn()} />);
    expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument();
  });

  it('calls onApply with job id when Apply is clicked', async () => {
    const user = userEvent.setup();
    const onApply = vi.fn();
    const job = makeJob({ id: 'job-77' });

    render(<JobCard job={job} onViewDetails={vi.fn()} onApply={onApply} />);
    await user.click(screen.getByRole('button', { name: 'Apply' }));

    expect(onApply).toHaveBeenCalledOnce();
    expect(onApply).toHaveBeenCalledWith('job-77');
  });
});
