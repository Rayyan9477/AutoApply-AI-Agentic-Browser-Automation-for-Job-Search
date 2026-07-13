import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { server } from '@/__tests__/mocks/server';
import AnalyticsPage from '@/pages/AnalyticsPage';

function renderAnalytics() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AnalyticsPage />
    </QueryClientProvider>,
  );
}

describe('AnalyticsPage (Insights)', () => {
  it('renders the application funnel stages', async () => {
    server.use(http.get('/api/v1/analytics/funnel', () => HttpResponse.json([{ stage: 'Applied', count: 45 }, { stage: 'Interview', count: 8 }])));
    server.use(http.get('/api/v1/analytics/ats-scores', () => HttpResponse.json([])));
    server.use(http.get('/api/v1/analytics/llm-usage', () => HttpResponse.json([])));
    server.use(http.get('/api/v1/analytics/timeline', () => HttpResponse.json([])));
    renderAnalytics();
    expect(await screen.findByText('Applied')).toBeInTheDocument();
    expect(screen.getByText('Interview')).toBeInTheDocument();
  });

  it('renders the ATS score distribution buckets', async () => {
    server.use(http.get('/api/v1/analytics/funnel', () => HttpResponse.json([])));
    server.use(http.get('/api/v1/analytics/ats-scores', () => HttpResponse.json([{ range_label: '76-100', count: 10 }, { range_label: '51-75', count: 20 }])));
    server.use(http.get('/api/v1/analytics/llm-usage', () => HttpResponse.json([])));
    server.use(http.get('/api/v1/analytics/timeline', () => HttpResponse.json([])));
    renderAnalytics();
    expect(await screen.findByText('76-100')).toBeInTheDocument();
    expect(screen.getByText('51-75')).toBeInTheDocument();
  });

  it('renders LLM usage by provider', async () => {
    server.use(http.get('/api/v1/analytics/funnel', () => HttpResponse.json([])));
    server.use(http.get('/api/v1/analytics/ats-scores', () => HttpResponse.json([])));
    server.use(http.get('/api/v1/analytics/llm-usage', () => HttpResponse.json([{ provider: 'openai', model: 'gpt-4o', total_requests: 100, total_tokens: 50000, total_cost_usd: 2.5, avg_latency_ms: 800 }])));
    server.use(http.get('/api/v1/analytics/timeline', () => HttpResponse.json([])));
    renderAnalytics();
    expect(await screen.findByText(/openai/i)).toBeInTheDocument();
  });
});
