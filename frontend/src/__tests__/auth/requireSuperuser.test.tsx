import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { RequireSuperuser } from '@/components/auth/RequireSuperuser';
import { useAuthStore } from '@/store/useAuthStore';

const base = { id: '1', email: 'a@x.com', full_name: null, is_active: true };

describe('RequireSuperuser', () => {
  beforeEach(() => useAuthStore.getState().clear());

  it('renders children for a superuser', () => {
    useAuthStore.getState().setAuth('t', { ...base, is_superuser: true });
    render(
      <MemoryRouter>
        <RequireSuperuser><div>admin content</div></RequireSuperuser>
      </MemoryRouter>,
    );
    expect(screen.getByText('admin content')).toBeInTheDocument();
  });

  it('shows the 403 state for a non-superuser', () => {
    useAuthStore.getState().setAuth('t', { ...base, is_superuser: false });
    render(
      <MemoryRouter>
        <RequireSuperuser><div>admin content</div></RequireSuperuser>
      </MemoryRouter>,
    );
    expect(screen.queryByText('admin content')).not.toBeInTheDocument();
    expect(screen.getByText('403')).toBeInTheDocument();
  });
});
