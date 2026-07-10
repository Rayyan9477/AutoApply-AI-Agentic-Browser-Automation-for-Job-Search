import { useLocation, useNavigate } from 'react-router-dom';

import Icon from '@/components/ui/Icon';
import { useUiStore } from '@/store/useUiStore';

const CRUMB: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/jobs': 'Jobs',
  '/applications': 'Applications',
  '/resumes': 'Résumés',
  '/analytics': 'Insights',
  '/settings': 'Settings',
};

export default function Header() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const current = CRUMB[pathname] ?? 'AutoApply AI';

  return (
    <header
      style={{
        flex: '0 0 auto', height: 60, display: 'flex', alignItems: 'center', gap: 14, padding: '0 20px',
        borderBottom: '1px solid var(--border)', background: 'color-mix(in srgb,var(--bg) 82%,transparent)',
        backdropFilter: 'blur(10px)', position: 'relative', zIndex: 15,
      }}
    >
      <button
        onClick={toggleSidebar}
        aria-label="Toggle sidebar"
        style={{
          flex: '0 0 auto', width: 32, height: 32, borderRadius: 'var(--r-md)', background: 'transparent',
          border: '1px solid transparent', color: 'var(--text-3)', cursor: 'pointer', display: 'grid', placeItems: 'center',
        }}
      >
        <Icon name="panel" size={18} />
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: '0 0 auto' }}>
        <span style={{ font: '600 12.5px/1 var(--font)', color: 'var(--text-3)', whiteSpace: 'nowrap' }}>Workspace</span>
        <span style={{ color: 'var(--text-4)', display: 'grid', placeItems: 'center' }}><Icon name="chevR" size={13} /></span>
        <span style={{ font: '700 14px/1 var(--font)', color: 'var(--text)', whiteSpace: 'nowrap', letterSpacing: '-.015em' }}>{current}</span>
      </div>

      <div style={{ flex: '1 1 auto' }} />

      <button
        onClick={() => navigate('/jobs')}
        aria-label="Search"
        style={{
          flex: '0 1 300px', minWidth: 120, display: 'flex', alignItems: 'center', gap: 9, height: 34,
          padding: '0 10px 0 11px', borderRadius: 'var(--r-md)', background: 'var(--surface-3)',
          border: '1px solid var(--border)', color: 'var(--text-3)', cursor: 'pointer', textAlign: 'left',
        }}
      >
        <span style={{ flex: '0 0 auto', display: 'grid', placeItems: 'center' }}><Icon name="search" size={16} /></span>
        <span style={{ flex: '1 1 auto', font: '500 12.5px/1 var(--font)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          Search jobs, applications, résumés…
        </span>
        <span style={{ flex: '0 0 auto', display: 'flex', gap: 2 }}>
          <kbd style={{ font: '600 10px/16px var(--mono)', color: 'var(--text-3)', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 4, padding: '0 4px', minWidth: 16, textAlign: 'center' }}>⌘</kbd>
          <kbd style={{ font: '600 10px/16px var(--mono)', color: 'var(--text-3)', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 4, padding: '0 5px' }}>K</kbd>
        </span>
      </button>

      <button
        aria-label="Activity"
        style={{
          flex: '0 0 auto', width: 34, height: 34, borderRadius: 'var(--r-md)', background: 'var(--surface-3)',
          border: '1px solid var(--border)', color: 'var(--text-2)', cursor: 'pointer', display: 'grid', placeItems: 'center',
        }}
      >
        <Icon name="bell" size={17} />
      </button>
    </header>
  );
}
