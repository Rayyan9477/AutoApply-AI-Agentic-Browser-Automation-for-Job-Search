import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { AuthShell, AuthField } from '@/components/auth/AuthShell';
import { authService } from '@/services/authService';
import { useAuthStore } from '@/store/useAuthStore';
import type { ApiError } from '@/types/api';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await authService.register({ email, password, full_name: fullName || undefined });
      // Auto-login after successful registration.
      const { access_token } = await authService.login(email, password);
      useAuthStore.setState({ token: access_token });
      const user = await authService.me();
      useAuthStore.getState().setAuth(access_token, user);
      navigate('/onboarding', { replace: true });
    } catch (err) {
      setError((err as ApiError).detail ?? 'Registration failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      title="Create your account"
      subtitle="Start applying on autopilot in minutes."
      error={error}
      onSubmit={handleSubmit}
      submitting={submitting}
      submitLabel={submitting ? 'Creating account…' : 'Create account'}
      footer={<>Already have an account? <Link to="/login" style={{ color: 'var(--accent)', fontWeight: 700, textDecoration: 'none' }}>Sign in</Link></>}
    >
      <AuthField id="fullName" label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" />
      <AuthField id="email" label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
      <AuthField id="password" label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" required />
    </AuthShell>
  );
}
