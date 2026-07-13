import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import { server } from '@/__tests__/mocks/server';
import DashboardPage from '@/pages/DashboardPage';

function dashStats() {
  return {
    total_jobs_found: 40, total_applications: 128, applications_pending: 3, applications_applied: 86,
    applications_interview: 11, applications_rejected: 8, applications_offer: 2, avg_ats_score: 0.82, total_llm_cost_usd: 14.62,
  };
}
function app(overrides: Record<string, unknown> = {}) {
  return {
    id: 'a1', job_id: 'j1', job_title: 'Senior Product Manager', company: 'Northwind Labs',
    resume_id: 'r1', status: 'applied', apply_mode: 'review', ats_score: 0.88, cover_letter_path: null,
    applied_at: '2026-07-08T10:00:00Z', response_date: null, notes: null,
    created_at: '2026-07-06T09:00:00Z', updated_at: '2026-07-08T10:00:00Z', ...overrides,
  };
}
const listOf = (...items: object[]) => ({ items, total: items.length, page: 1, page_size: 20, has_next: false });

function renderDash() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter><DashboardPage /></MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('DashboardPage live-now card', () => {
  it('shows a Live now card for an in-flight (applying) application', async () => {
    server.use(http.get('/api/v1/analytics/dashboard', () => HttpResponse.json(dashStats())));
    server.use(http.get('/api/v1/applications/', () => HttpResponse.json(listOf(app({ status: 'applying', job_title: 'Live PM Role' })))));
    renderDash();
    expect(await screen.findByText(/live now/i)).toBeInTheDocument();
    expect(screen.getAllByText('Live PM Role').length).toBeGreaterThan(0);
  });

  it('does not show a Live now card when nothing is in flight', async () => {
    server.use(http.get('/api/v1/analytics/dashboard', () => HttpResponse.json(dashStats())));
    server.use(http.get('/api/v1/applications/', () => HttpResponse.json(listOf(app({ status: 'applied' })))));
    renderDash();
    await screen.findByText('Senior Product Manager');
    expect(screen.queryByText(/live now/i)).not.toBeInTheDocument();
  });
});
