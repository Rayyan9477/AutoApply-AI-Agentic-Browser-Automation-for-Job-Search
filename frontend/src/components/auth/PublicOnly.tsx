import { type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';

import { useAuthStore } from '@/store/useAuthStore';

/**
 * Redirects already-authenticated users away from public pages (login/register).
 * `redirectTo` lets a page send new users somewhere other than the dashboard — the register
 * route uses `/onboarding` so a just-registered user is not bounced past onboarding by this
 * guard racing RegisterPage's own navigation.
 */
export function PublicOnly({
  children,
  redirectTo = '/dashboard',
}: {
  children: ReactNode;
  redirectTo?: string;
}) {
  const status = useAuthStore((s) => s.status);

  if (status === 'authenticated') {
    return <Navigate to={redirectTo} replace />;
  }
  return <>{children}</>;
}
