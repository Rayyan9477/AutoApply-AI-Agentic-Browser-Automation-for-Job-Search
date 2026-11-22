import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { server } from '@/__tests__/mocks/server';
import ApplicationsPage from '@/pages/ApplicationsPage';

function app(overrides: Record<string, unknown> = {}) {
  return {
    id: 'a1', job_id: 'j1', job_title: 'Group Product Manager', company: 'Cardinal Health',
    resume_id: 'r1', status: 'pending_review', apply_mode: 'review', ats_score: 0.88,
    cover_letter_path: null, applied_at: null, response_date: null, notes: null,
    created_at: '2026-07-06T09:00:00Z', updated_at: '2026-07-06T09:00:00Z', ...overrides,
  };
}

const listOf = (...items: object[]) => ({ items, total: items.length, page: 1, page_size: 20, has_next: false });

function renderApps() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/applications']}>
        <Routes>
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/applications/:id" element={<div>detail</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ApplicationsPage', () => {
  it('renders application rows from the API', async () => {
    server.use(http.get('/api/v1/applications/', () => HttpResponse.json(listOf(app(), app({ id: 'a2', job_title: 'Staff PM', status: 'applied' })))));
    renderApps();
    expect(await screen.findByText('Group Product Manager')).toBeInTheDocument();
    expect(screen.getByText('Staff PM')).toBeInTheDocument();
  });

  it('renders the ATS score as a 0–100 percentage (API returns a 0–1 float)', async () => {
    server.use(http.get('/api/v1/applications/', () => HttpResponse.json(listOf(app({ ats_score: 0.91 })))));
    renderApps();
    await screen.findByText('Group Product Manager');
    expect(screen.getByText('91')).toBeInTheDocument();
  });

  it('has a "Needs review" status filter tab that becomes active when clicked', async () => {
    server.use(http.get('/api/v1/applications/', () => HttpResponse.json(listOf(app()))));
    renderApps();
    await screen.findByText('Group Product Manager');
    const tab = screen.getByRole('tab', { name: /needs review/i });
    await userEvent.click(tab);
    expect(tab).toHaveAttribute('aria-selected', 'true');
  });

  it('bulk-approves selected applications via the endpoint', async () => {
    server.use(http.get('/api/v1/applications/', () => HttpResponse.json(listOf(app()))));
    let body: { application_ids?: string[] } | null = null;
    server.use(http.post('/api/v1/applications/bulk-approve', async ({ request }) => {
      body = (await request.json()) as { application_ids: string[] };
      return HttpResponse.json({ approved: 1 });
    }));

    renderApps();
    await screen.findByText('Group Product Manager');
    await userEvent.click(screen.getByRole('checkbox', { name: /select group product manager/i }));
    await userEvent.click(screen.getByRole('button', { name: /approve/i }));

    await waitFor(() => expect(body).not.toBeNull());
    expect(body!.application_ids).toContain('a1');
  });
});
