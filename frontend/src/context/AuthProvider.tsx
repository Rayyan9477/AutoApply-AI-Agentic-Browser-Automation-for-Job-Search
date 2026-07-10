import { useEffect, type ReactNode } from 'react';

import { authService } from '@/services/authService';
import { useAuthStore } from '@/store/useAuthStore';

/**
 * Initializes auth state on boot via a silent refresh (httpOnly cookie). In Phase 0
 * the `/auth/refresh` endpoint does not exist yet, so boot resolves to
 * "unauthenticated" and the user logs in explicitly; Phase 1 enables persistence.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const status = useAuthStore((s) => s.status);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const { access_token } = await authService.refresh();
        // Attach the token (keep status 'loading') so the me() call is authenticated.
        useAuthStore.setState({ token: access_token });
        const user = await authService.me();
        if (active) {
          useAuthStore.getState().setAuth(access_token, user);
        }
      } catch {
        if (active) {
          useAuthStore.getState().clear();
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (status === 'loading') {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--bg)' }}>
        <div
          aria-label="Loading"
          style={{ width: 32, height: 32, borderRadius: '50%', border: '3px solid var(--surface-2)', borderTopColor: 'var(--accent)', animation: 'aaSpin .8s linear infinite' }}
        />
      </div>
    );
  }

  return <>{children}</>;
}
