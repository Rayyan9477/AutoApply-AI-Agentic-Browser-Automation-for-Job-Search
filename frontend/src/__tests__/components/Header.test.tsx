import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import Header from '@/components/layout/Header';

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Header />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Header breadcrumb', () => {
  it('shows "System health" on the /admin route (BUG-007)', () => {
    renderAt('/admin');
    expect(screen.getByText('System health')).toBeInTheDocument();
  });

  it('shows the mapped label for a known route', () => {
    renderAt('/jobs');
    expect(screen.getByText('Jobs')).toBeInTheDocument();
  });

  it('falls back to the app title on an unknown route', () => {
    renderAt('/nope');
    expect(screen.getByText('AutoApply AI')).toBeInTheDocument();
  });
});

describe('Header controls', () => {
  it('has no dead activity bell button', () => {
    renderAt('/dashboard');
    expect(screen.queryByRole('button', { name: /activity/i })).not.toBeInTheDocument();
  });

  it('shows a platform-aware shortcut hint (Ctrl on non-Mac)', () => {
    renderAt('/dashboard'); // jsdom navigator.platform is '' → non-Mac
    expect(screen.getByText('Ctrl')).toBeInTheDocument();
    expect(screen.queryByText('⌘')).not.toBeInTheDocument();
  });
});
