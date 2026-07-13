import { Link } from 'react-router-dom';

import Icon, { type IconName } from '@/components/ui/Icon';

type SysCode = '404' | '403' | '500';

const STATES: Record<SysCode, { icon: IconName; title: string; desc: string }> = {
  '404': {
    icon: 'search',
    title: 'Page not found',
    desc: "The page you're looking for doesn't exist or may have moved.",
  },
  '403': {
    icon: 'lock',
    title: 'Access denied',
    desc: "You don't have permission to view this page.",
  },
  '500': {
    icon: 'alert',
    title: 'Something went wrong',
    desc: 'An unexpected error occurred on our end. Please try again in a moment.',
  },
};

/** Full-bleed 404 / 403 / 500 state, ported from the design's SYSTEM STATE section. */
export default function SystemStatePage({ code }: { code: SysCode }) {
  const s = STATES[code];
  return (
    <div style={{ minHeight: '70vh', display: 'grid', placeItems: 'center', padding: 24, color: 'var(--text)', fontFamily: 'var(--font)' }}>
      <div style={{ textAlign: 'center', maxWidth: 420 }}>
        <div style={{ width: 64, height: 64, margin: '0 auto 20px', borderRadius: 16, background: 'var(--accent-soft)', border: '1px solid var(--accent-line)', display: 'grid', placeItems: 'center', color: 'var(--accent)' }}>
          <Icon name={s.icon} size={28} sw={1.8} />
        </div>
        <div style={{ font: '800 64px/1 var(--font)', letterSpacing: '-.04em', color: 'var(--text)' }}>{code}</div>
        <h1 style={{ margin: '16px 0 0', font: '800 22px/1.15 var(--font)', letterSpacing: '-.02em' }}>{s.title}</h1>
        <p style={{ margin: '10px auto 24px', maxWidth: 340, font: '500 13.5px/1.55 var(--font)', color: 'var(--text-3)' }}>{s.desc}</p>
        <Link to="/dashboard" style={{ display: 'inline-flex', alignItems: 'center', height: 42, padding: '0 20px', borderRadius: 'var(--r-md)', background: 'var(--accent)', color: 'var(--accent-ink)', font: '700 13px/1 var(--font)', textDecoration: 'none' }}>
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
