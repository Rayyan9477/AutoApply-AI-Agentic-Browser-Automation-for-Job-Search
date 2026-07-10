import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { RunTimeline } from '@/components/applications/RunTimeline';
import type { TimelineStep } from '@/lib/timeline';

const steps: TimelineStep[] = [
  { key: 'queued', label: 'Queued', desc: 'Added to the apply queue', state: 'done' },
  { key: 'applying', label: 'Applying', desc: '', state: 'failed', diag: 'Form changed mid-run.' },
];

describe('RunTimeline', () => {
  it('renders each step label', () => {
    render(<RunTimeline steps={steps} />);
    expect(screen.getByText('Queued')).toBeInTheDocument();
    expect(screen.getByText('Applying')).toBeInTheDocument();
  });

  it('renders a step description when present', () => {
    render(<RunTimeline steps={steps} />);
    expect(screen.getByText('Added to the apply queue')).toBeInTheDocument();
  });

  it('shows the diagnosis for a failed step', () => {
    render(<RunTimeline steps={steps} />);
    expect(screen.getByText('Form changed mid-run.')).toBeInTheDocument();
  });

  it('exposes one node per step with its state for the caller/tests', () => {
    render(<RunTimeline steps={steps} />);
    const nodes = document.querySelectorAll('[data-step]');
    expect(nodes.length).toBe(2);
    expect(document.querySelector('[data-step="applying"]')?.getAttribute('data-state')).toBe('failed');
  });

  it('renders no step nodes for an empty timeline', () => {
    render(<RunTimeline steps={[]} />);
    expect(document.querySelectorAll('[data-step]').length).toBe(0);
  });
});
