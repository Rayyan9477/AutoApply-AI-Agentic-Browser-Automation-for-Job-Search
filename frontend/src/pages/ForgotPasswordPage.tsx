import { Link } from 'react-router-dom';

import Icon from '@/components/ui/Icon';

/**
 * Password-reset request screen. Ported faithfully from the design's AUTH → "Reset your password"
 * state, which intentionally ships as a disabled "COMING SOON" stub (no backend reset endpoint yet).
 */
export default function ForgotPasswordPage() {
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--bg)', color: 'var(--text)', fontFamily: 'var(--font)', letterSpacing: '-.01em', padding: 20 }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'center', marginBottom: 22 }}>
          <div style={{ width: 32, height: 32, borderRadius: 9, background: 'var(--accent-soft)', border: '1px solid var(--accent-line)', display: 'grid', placeItems: 'center', color: 'var(--accent)', boxShadow: 'inset 0 0 14px var(--accent-glow)' }}>
            <Icon name="cpu" size={18} sw={1.9} />
          </div>
          <div style={{ font: '800 17px/1 var(--font)', letterSpacing: '-.02em' }}>AutoApply<span style={{ color: 'var(--accent)' }}> AI</span></div>
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-2)', padding: 26 }}>
          <h1 style={{ margin: '0 0 5px', font: '800 20px/1.2 var(--font)', letterSpacing: '-.02em' }}>Reset your password</h1>
          <p style={{ margin: '0 0 20px', font: '500 12.5px/1.4 var(--font)', color: 'var(--text-3)' }}>Enter your email and we’ll send you a reset link.</p>

          <label htmlFor="reset-email" style={{ display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 14 }}>
            <span style={{ font: '600 11.5px/1 var(--font)', color: 'var(--text-2)' }}>Email</span>
            <input id="reset-email" type="email" placeholder="you@email.com" autoComplete="email"
              style={{ height: 40, padding: '0 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-3)', border: '1px solid var(--border)', color: 'var(--text)', font: '500 13px/1 var(--font)', outline: 'none' }} />
          </label>

          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 10px', marginBottom: 12, borderRadius: 6, background: 'var(--review-soft)', color: 'var(--review)', font: '700 10px/1 var(--mono)', letterSpacing: '.06em' }}>
            COMING SOON
          </span>

          <button type="button" disabled
            style={{ width: '100%', height: 42, borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-4)', font: '700 13px/1 var(--font)', cursor: 'not-allowed' }}>
            Send reset link
          </button>
        </div>

        <div style={{ textAlign: 'center', marginTop: 16, font: '500 12.5px/1.4 var(--font)', color: 'var(--text-3)' }}>
          Remembered it? <Link to="/login" style={{ color: 'var(--accent)', fontWeight: 700, textDecoration: 'none' }}>Back to sign in</Link>
        </div>
      </div>
    </div>
  );
}
