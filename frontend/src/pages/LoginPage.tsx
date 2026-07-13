import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { AuthShell, AuthField } from '@/components/auth/AuthShell';
import { authService } from '@/services/authService';
import { useAuthStore } from '@/store/useAuthStore';
import type { ApiError } from '@/types/api';

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { access_token } = await authService.login(email, password);
      useAuthStore.setState({ token: access_token });
      const user = await authService.me();
      useAuthStore.getState().setAuth(access_token, user);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError((err as ApiError).detail ?? 'Login failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to your job-search copilot."
      error={error}
      onSubmit={handleSubmit}
      submitting={submitting}
      submitLabel={submitting ? 'Signing in…' : 'Sign in'}
      footer={<>No account? <Link to="/register" style={{ color: 'var(--accent)', fontWeight: 700, textDecoration: 'none' }}>Create one</Link></>}
    >
      <AuthField id="email" label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
      <AuthField id="password" label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
      <div style={{ textAlign: 'right', margin: '-4px 0 10px' }}>
        <Link to="/forgot-password" style={{ font: '600 12px/1 var(--font)', color: 'var(--accent)', textDecoration: 'none' }}>Forgot password?</Link>
      </div>
    </AuthShell>
  );
}
