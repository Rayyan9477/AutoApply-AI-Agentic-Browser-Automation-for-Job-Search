import type { FormEvent, ReactNode } from 'react';

import Icon from '@/components/ui/Icon';

interface AuthShellProps {
  title: string;
  subtitle: string;
  error?: string | null;
  submitLabel: string;
  submitting?: boolean;
  onSubmit: (e: FormEvent) => void;
  children: ReactNode;
  footer: ReactNode;
}

/** Centered brand card used by the sign-in / register screens. */
export function AuthShell({ title, subtitle, error, submitLabel, submitting, onSubmit, children, footer }: AuthShellProps) {
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--bg)', color: 'var(--text)', fontFamily: 'var(--font)', letterSpacing: '-.01em', padding: 20 }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'center', marginBottom: 22 }}>
          <div style={{ width: 32, height: 32, borderRadius: 9, background: 'var(--accent-soft)', border: '1px solid var(--accent-line)', display: 'grid', placeItems: 'center', color: 'var(--accent)', boxShadow: 'inset 0 0 14px var(--accent-glow)' }}>
            <Icon name="cpu" size={18} sw={1.9} />
          </div>
          <div style={{ font: '800 17px/1 var(--font)', letterSpacing: '-.02em' }}>AutoApply<span style={{ color: 'var(--accent)' }}> AI</span></div>
        </div>

        <form onSubmit={onSubmit} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-2)', padding: 26 }}>
          <h1 style={{ margin: '0 0 5px', font: '800 20px/1.2 var(--font)', letterSpacing: '-.02em' }}>{title}</h1>
          <p style={{ margin: '0 0 20px', font: '500 12.5px/1.4 var(--font)', color: 'var(--text-3)' }}>{subtitle}</p>
          {error && (
            <div role="alert" style={{ display: 'flex', gap: 9, alignItems: 'center', padding: '10px 12px', marginBottom: 16, borderRadius: 'var(--r-md)', background: 'var(--rejected-soft)', border: '1px solid var(--rejected)', color: 'var(--rejected)', font: '600 12px/1.35 var(--font)' }}>
              <Icon name="alert" size={15} /> {error}
            </div>
          )}
          {children}
          <button type="submit" disabled={submitting} style={{ width: '100%', height: 42, marginTop: 6, borderRadius: 'var(--r-md)', background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', font: '700 13px/1 var(--font)', cursor: submitting ? 'default' : 'pointer', opacity: submitting ? 0.7 : 1 }}>
            {submitLabel}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: 16, font: '500 12.5px/1.4 var(--font)', color: 'var(--text-3)' }}>{footer}</div>
      </div>
    </div>
  );
}

interface AuthFieldProps {
  id: string;
  label: string;
  type?: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  autoComplete?: string;
  required?: boolean;
}

export function AuthField({ id, label, type = 'text', value, onChange, autoComplete, required }: AuthFieldProps) {
  return (
    <label htmlFor={id} style={{ display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 14 }}>
      <span style={{ font: '600 11.5px/1 var(--font)', color: 'var(--text-2)' }}>{label}</span>
      <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        required={required}
        style={{ height: 40, padding: '0 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-3)', border: '1px solid var(--border)', color: 'var(--text)', font: '500 13px/1 var(--font)', outline: 'none' }}
      />
    </label>
  );
}
