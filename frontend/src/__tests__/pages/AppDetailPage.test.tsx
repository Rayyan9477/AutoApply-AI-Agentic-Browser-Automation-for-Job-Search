import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { server } from '@/__tests__/mocks/server';
import AppDetailPage from '@/pages/AppDetailPage';

function fullApp(overrides: Record<string, unknown> = {}) {
  return {
    id: 'app-1', job_id: 'job-1', job_title: 'Senior Product Manager', company: 'Northwind Labs',
    resume_id: 'resume-1', status: 'applied', apply_mode: 'review', ats_score: 0.91,
    cover_letter_path: null, applied_at: '2026-07-08T10:00:00Z', response_date: null, notes: null,
    created_at: '2026-07-06T09:00:00Z', updated_at: '2026-07-08T10:00:00Z', ...overrides,
  };
}

function renderDetail(appId = 'app-1') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/applications/${appId}`]}>
        <Routes>
          <Route path="/applications/:id" element={<AppDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AppDetailPage', () => {
  it('shows the application job title and company once loaded', async () => {
    server.use(http.get('/api/v1/applications/:appId', () => HttpResponse.json(fullApp())));
    renderDetail();
    expect(await screen.findByText('Senior Product Manager')).toBeInTheDocument();
    // Company is shown in the subtitle line (combined with mode + date), so match on substring.
    expect(screen.getByText(/Northwind Labs/)).toBeInTheDocument();
  });

  it('renders the run timeline for the application status + mode', async () => {
    server.use(http.get('/api/v1/applications/:appId', () => HttpResponse.json(fullApp({ status: 'applied', apply_mode: 'review' }))));
    renderDetail();
    await screen.findByText('Senior Product Manager');
    // review-mode applied → the "Applied" step is the current one in the timeline.
    const applied = document.querySelector('[data-step="applied"]');
    expect(applied).not.toBeNull();
    expect(applied?.getAttribute('data-state')).toBe('current');
  });

  it('surfaces the failure diagnosis for a failed run', async () => {
    server.use(http.get('/api/v1/applications/:appId', () => HttpResponse.json(fullApp({ status: 'failed', apply_mode: 'autonomous' }))));
    renderDetail();
    await screen.findByText('Senior Product Manager');
    expect(document.querySelector('[data-step="applying"]')?.getAttribute('data-state')).toBe('failed');
  });
});
