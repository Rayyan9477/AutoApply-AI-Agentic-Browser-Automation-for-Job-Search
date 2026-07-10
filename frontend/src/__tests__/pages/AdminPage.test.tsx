import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { server } from '@/__tests__/mocks/server';
import AdminPage from '@/pages/AdminPage';

function issue(overrides: Record<string, unknown> = {}) {
  return {
    id: 'i1', user_id: null, category: 'apply_failure_rate', severity: 'critical',
    signals: { total: 6, failed: 4 }, diagnosis: '4/6 apps FAILED in the last 6h',
    status: 'open', detected_at: '2026-07-10T10:00:00Z', created_at: '2026-07-10T10:00:00Z', ...overrides,
  };
}

function renderAdmin() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><AdminPage /></QueryClientProvider>,
  );
}

describe('AdminPage (system health)', () => {
  it('renders harness-detected system issues', async () => {
    server.use(http.get('/api/v1/admin/system-issues', () => HttpResponse.json([
      issue(),
      issue({ id: 'i2', category: 'queue_depth', severity: 'warning', diagnosis: 'Queue backlog: 120' }),
    ])));
    renderAdmin();
    expect(await screen.findByText(/apply_failure_rate/i)).toBeInTheDocument();
    expect(screen.getByText(/queue backlog: 120/i)).toBeInTheDocument();
  });

  it('shows an all-clear state when there are no issues', async () => {
    server.use(http.get('/api/v1/admin/system-issues', () => HttpResponse.json([])));
    renderAdmin();
    expect(await screen.findByText(/all clear|no issues|healthy/i)).toBeInTheDocument();
  });

  it('filters by status when a tab is clicked', async () => {
    let lastUrl = '';
    server.use(http.get('/api/v1/admin/system-issues', ({ request }) => { lastUrl = request.url; return HttpResponse.json([issue()]); }));
    renderAdmin();
    await screen.findByText(/apply_failure_rate/i);
    await userEvent.click(screen.getByRole('tab', { name: /open/i }));
    await waitFor(() => expect(lastUrl).toMatch(/status=open/));
  });
});
