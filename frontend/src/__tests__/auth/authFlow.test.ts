import { describe, it, expect, beforeEach } from 'vitest';

import { authService } from '@/services/authService';
import { useAuthStore } from '@/store/useAuthStore';

const sampleUser = {
  id: 'u1',
  email: 'a@x.com',
  full_name: null,
  is_active: true,
};

describe('useAuthStore', () => {
  beforeEach(() => useAuthStore.getState().clear());

  it('setAuth marks the session authenticated', () => {
    useAuthStore.getState().setAuth('tok', sampleUser);
    const s = useAuthStore.getState();
    expect(s.token).toBe('tok');
    expect(s.status).toBe('authenticated');
    expect(s.user?.email).toBe('a@x.com');
  });

  it('clear de-authenticates the session', () => {
    useAuthStore.getState().setAuth('tok', sampleUser);
    useAuthStore.getState().clear();
    const s = useAuthStore.getState();
    expect(s.token).toBeNull();
    expect(s.status).toBe('unauthenticated');
  });
});

describe('authService (MSW-backed)', () => {
  beforeEach(() => useAuthStore.getState().clear());

  it('register returns the created user', async () => {
    const user = await authService.register({ email: 'new@x.com', password: 'password123' });
    expect(user.email).toBe('new@x.com');
  });

  it('login returns an access token', async () => {
    const res = await authService.login('a@x.com', 'password123');
    expect(res.access_token).toBe('test-access-token');
  });

  it('me attaches the bearer token via the interceptor', async () => {
    useAuthStore.getState().setAuth('test-access-token', {
      ...sampleUser,
      email: 'test@example.com',
    });
    const user = await authService.me();
    expect(user.email).toBe('test@example.com');
  });
});
