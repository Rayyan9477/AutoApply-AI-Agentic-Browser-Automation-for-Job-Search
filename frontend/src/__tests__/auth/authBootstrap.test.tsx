import { describe, it, expect, beforeEach } from 'vitest';
import { StrictMode } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { AuthProvider } from '@/context/AuthProvider';
import { server } from '@/__tests__/mocks/server';
import { useAuthStore } from '@/store/useAuthStore';

describe('AuthProvider boot refresh', () => {
  beforeEach(() => useAuthStore.getState().clear());

  it('issues only one /auth/refresh even when the effect double-invokes (StrictMode)', async () => {
    // A rotating-refresh backend revokes the whole token family if the *same* refresh
    // cookie is presented twice. React StrictMode double-invokes mount effects in dev,
    // and multiple tabs do the same in prod — so the boot refresh must be single-flighted.
    let refreshCalls = 0;
    server.use(
      http.post('/api/v1/auth/refresh', () => {
        refreshCalls += 1;
        return HttpResponse.json({ access_token: 'boot-token', token_type: 'bearer' });
      }),
      http.get('/api/v1/auth/me', () =>
        HttpResponse.json({ id: 'u1', email: 'boot@x.com', full_name: null, is_active: true }),
      ),
    );

    render(
      <StrictMode>
        <AuthProvider>
          <div>ready</div>
        </AuthProvider>
      </StrictMode>,
    );

    await waitFor(() => expect(useAuthStore.getState().status).toBe('authenticated'));
    expect(screen.getByText('ready')).toBeInTheDocument();
    expect(refreshCalls).toBe(1);
  });
});
