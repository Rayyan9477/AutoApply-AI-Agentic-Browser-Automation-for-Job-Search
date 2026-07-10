import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

import { PublicOnly } from '@/components/auth/PublicOnly';
import { useAuthStore } from '@/store/useAuthStore';

const user = { id: 'u1', email: 'a@x.com', full_name: null, is_active: true };

describe('PublicOnly', () => {
  beforeEach(() => useAuthStore.getState().clear());

  it('sends a freshly authenticated user to redirectTo (e.g. onboarding after register), not /dashboard', async () => {
    // Registration flips auth to authenticated while still on /register. Without an explicit
    // target, PublicOnly would bounce the new user straight to /dashboard and skip onboarding.
    render(
      <MemoryRouter initialEntries={['/register']}>
        <Routes>
          <Route
            path="/register"
            element={<PublicOnly redirectTo="/onboarding"><div>register form</div></PublicOnly>}
          />
          <Route path="/onboarding" element={<div>onboarding screen</div>} />
          <Route path="/dashboard" element={<div>dashboard screen</div>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText('register form')).toBeInTheDocument();

    act(() => useAuthStore.getState().setAuth('tok', user));

    expect(await screen.findByText('onboarding screen')).toBeInTheDocument();
    expect(screen.queryByText('dashboard screen')).not.toBeInTheDocument();
  });

  it('defaults to /dashboard when no redirectTo is given', async () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<PublicOnly><div>login form</div></PublicOnly>} />
          <Route path="/dashboard" element={<div>dashboard screen</div>} />
        </Routes>
      </MemoryRouter>,
    );

    act(() => useAuthStore.getState().setAuth('tok', user));

    expect(await screen.findByText('dashboard screen')).toBeInTheDocument();
  });
});
