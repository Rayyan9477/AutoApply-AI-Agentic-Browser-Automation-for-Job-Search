import { http, HttpResponse } from 'msw';
import { describe, it, expect, beforeEach } from 'vitest';

import { server } from '@/__tests__/mocks/server';
import api from '@/services/api';
import { useAuthStore } from '@/store/useAuthStore';

const sampleUser = { id: 'u1', email: 'a@x.com', full_name: null, is_active: true };
const ok = () =>
  HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20, has_next: false });

describe('api 401 refresh interceptor (M5)', () => {
  beforeEach(() => useAuthStore.getState().clear());

  it('refreshes the token on 401 and retries the original request', async () => {
    useAuthStore.getState().setAuth('stale-token', sampleUser);
    let refreshCalls = 0;
    server.use(
      http.get('/api/v1/applications/', ({ request }) =>
        request.headers.get('Authorization') === 'Bearer fresh-token'
          ? ok()
          : new HttpResponse(null, { status: 401 }),
      ),
      http.post('/api/v1/auth/refresh', () => {
        refreshCalls += 1;
        return HttpResponse.json({ access_token: 'fresh-token', token_type: 'bearer' });
      }),
    );

    const res = await api.get('/applications/');
    expect(res.status).toBe(200);
    expect(useAuthStore.getState().token).toBe('fresh-token');
    expect(refreshCalls).toBe(1);
  });

  it('dedups concurrent 401s into a single refresh call', async () => {
    useAuthStore.getState().setAuth('stale-token', sampleUser);
    let refreshCalls = 0;
    server.use(
      http.get('/api/v1/applications/', ({ request }) =>
        request.headers.get('Authorization') === 'Bearer fresh-token'
          ? ok()
          : new HttpResponse(null, { status: 401 }),
      ),
      http.post('/api/v1/auth/refresh', () => {
        refreshCalls += 1;
        return HttpResponse.json({ access_token: 'fresh-token', token_type: 'bearer' });
      }),
    );

    const [a, b] = await Promise.all([api.get('/applications/'), api.get('/applications/')]);
    expect(a.status).toBe(200);
    expect(b.status).toBe(200);
    expect(refreshCalls).toBe(1);
  });

  it('clears auth when the refresh itself fails', async () => {
    useAuthStore.getState().setAuth('stale-token', sampleUser);
    server.use(
      http.get('/api/v1/applications/', () => new HttpResponse(null, { status: 401 })),
      http.post('/api/v1/auth/refresh', () => new HttpResponse(null, { status: 401 })),
    );

    await expect(api.get('/applications/')).rejects.toMatchObject({ status_code: 401 });
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().status).toBe('unauthenticated');
  });
});
