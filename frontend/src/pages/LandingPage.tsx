import { Link } from 'react-router-dom';

import Icon, { type IconName } from '@/components/ui/Icon';

const FEATURES: { icon: IconName; title: string; sub: string }[] = [
  { icon: 'search', title: 'Multi-platform search', sub: 'LinkedIn, Indeed, Glassdoor, and Exa — one query, ranked matches.' },
  { icon: 'file', title: 'Résumés that pass ATS', sub: 'The agent tailors and optimizes your résumé per role and scores every match.' },
  { icon: 'cpu', title: 'Applies for you', sub: 'Review each, batch-approve, or go fully autonomous. You stay in control.' },
  { icon: 'activity', title: 'Live, transparent runs', sub: 'Watch every step in real time and step in for CAPTCHAs when needed.' },
  { icon: 'chart', title: 'Insights that matter', sub: 'Funnel, match quality, activity, and AI spend — all in one view.' },
  { icon: 'key', title: 'Bring your own key', sub: 'Your LLM keys, encrypted at rest. No lock-in, no surprise bills.' },
];

const linkBtn = (primary: boolean): React.CSSProperties => ({
  display: 'inline-flex', alignItems: 'center', gap: 8, height: 44, padding: '0 20px', borderRadius: 'var(--r-md)',
  textDecoration: 'none', font: '700 13.5px/1 var(--font)', cursor: 'pointer',
  background: primary ? 'var(--accent)' : 'transparent', border: `1px solid ${primary ? 'var(--accent)' : 'var(--border-2)'}`,
  color: primary ? 'var(--accent-ink)' : 'var(--text)',
  boxShadow: primary ? '0 0 0 1px var(--accent-line),0 8px 24px -10px var(--accent-glow)' : 'none',
});

export default function LandingPage() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', fontFamily: 'var(--font)', letterSpacing: '-.01em' }}>
      {/* Nav */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', maxWidth: 1120, margin: '0 auto', padding: '20px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 9, background: 'var(--accent-soft)', border: '1px solid var(--accent-line)', display: 'grid', placeItems: 'center', color: 'var(--accent)' }}><Icon name="cpu" size={18} sw={1.9} /></div>
          <div style={{ font: '800 16px/1 var(--font)', letterSpacing: '-.02em' }}>AutoApply<span style={{ color: 'var(--accent)' }}> AI</span></div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link to="/login" style={{ font: '700 13px/1 var(--font)', color: 'var(--text-2)', textDecoration: 'none' }}>Sign in</Link>
          <Link to="/register" style={linkBtn(true)}>Get started</Link>
        </div>
      </header>

      {/* Hero */}
      <section style={{ maxWidth: 820, margin: '0 auto', padding: '70px 24px 40px', textAlign: 'center' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 28, padding: '0 12px', borderRadius: 999, background: 'var(--accent-soft)', border: '1px solid var(--accent-line)', color: 'var(--accent)', font: '600 11.5px/1 var(--mono)', letterSpacing: '.04em', marginBottom: 22 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)' }} /> AGENTIC JOB SEARCH
        </span>
        <h1 style={{ margin: 0, font: '800 46px/1.08 var(--font)', letterSpacing: '-.035em' }}>
          Your job search,<br /><span style={{ color: 'var(--accent)' }}>on autopilot.</span>
        </h1>
        <p style={{ margin: '20px auto 0', maxWidth: 560, font: '500 16px/1.5 var(--font)', color: 'var(--text-3)' }}>
          AutoApply AI searches across platforms, tailors your résumé to each role, and submits applications — with you approving every step, or none at all.
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 30, flexWrap: 'wrap' }}>
          <Link to="/register" style={linkBtn(true)}><Icon name="search" size={16} sw={2} /> Get started free</Link>
          <Link to="/login" style={linkBtn(false)}>Sign in</Link>
        </div>
      </section>

      {/* Features */}
      <section style={{ maxWidth: 1000, margin: '0 auto', padding: '30px 24px 80px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 16 }}>
          {FEATURES.map((f) => (
            <div key={f.title} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-1)', padding: 20 }}>
              <span style={{ display: 'grid', placeItems: 'center', width: 40, height: 40, borderRadius: 11, background: 'var(--accent-soft)', color: 'var(--accent)', marginBottom: 14 }}><Icon name={f.icon} size={19} /></span>
              <div style={{ font: '700 15px/1.3 var(--font)' }}>{f.title}</div>
              <p style={{ margin: '7px 0 0', font: '500 13px/1.5 var(--font)', color: 'var(--text-3)' }}>{f.sub}</p>
            </div>
          ))}
        </div>
      </section>

      <footer style={{ borderTop: '1px solid var(--border)', padding: '22px 24px', textAlign: 'center', font: '500 12px/1.4 var(--font)', color: 'var(--text-4)' }}>
        AutoApply AI · Bring your own key · You stay in control.
      </footer>
    </div>
  );
}
