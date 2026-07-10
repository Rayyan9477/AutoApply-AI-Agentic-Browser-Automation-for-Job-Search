import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';

import Icon, { type IconName } from '@/components/ui/Icon';
import api from '@/services/api';
import { useAuthStore } from '@/store/useAuthStore';
import { useUiStore } from '@/store/useUiStore';

export const SIDEBAR_W_EXPANDED = 244;
export const SIDEBAR_W_COLLAPSED = 64;

interface NavItem {
  to: string;
  label: string;
  icon: IconName;
}

const NAV: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: 'grid' },
  { to: '/jobs', label: 'Jobs', icon: 'briefcase' },
  { to: '/applications', label: 'Applications', icon: 'inbox' },
  { to: '/resumes', label: 'Résumés', icon: 'file' },
  { to: '/analytics', label: 'Insights', icon: 'chart' },
  { to: '/settings', label: 'Settings', icon: 'sliders' },
];

function initials(name?: string | null, email?: string): string {
  if (name && name.trim()) {
    const parts = name.trim().split(/\s+/);
    return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase();
  }
  return (email ?? 'U').slice(0, 2).toUpperCase();
}

export default function Sidebar() {
  const navigate = useNavigate();
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const theme = useUiStore((s) => s.theme);
  const density = useUiStore((s) => s.density);
  const toggleTheme = useUiStore((s) => s.toggleTheme);
  const toggleDensity = useUiStore((s) => s.toggleDensity);
  const user = useAuthStore((s) => s.user);
  const clear = useAuthStore((s) => s.clear);
  const [menuOpen, setMenuOpen] = useState(false);
  const expanded = !collapsed;
  const nav = user?.is_superuser
    ? [...NAV, { to: '/admin', label: 'System health', icon: 'shield' as const }]
    : NAV;

  const signOut = () => {
    api.post('/auth/logout').catch(() => {});
    clear();
    navigate('/login');
  };

  return (
    <aside
      style={{
        flex: '0 0 auto',
        width: expanded ? SIDEBAR_W_EXPANDED : SIDEBAR_W_COLLAPSED,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-2)',
        borderRight: '1px solid var(--border)',
        transition: 'width .22s var(--ease)',
        zIndex: 20,
      }}
    >
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '16px 15px 14px', height: 60 }}>
        <div
          style={{
            width: 30, height: 30, borderRadius: 9, background: 'var(--accent-soft)',
            border: '1px solid var(--accent-line)', display: 'grid', placeItems: 'center',
            color: 'var(--accent)', boxShadow: 'inset 0 0 14px var(--accent-glow)', flex: '0 0 auto',
          }}
        >
          <Icon name="cpu" size={17} sw={1.9} />
        </div>
        {expanded && (
          <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <div style={{ font: '800 15px/1 var(--font)', letterSpacing: '-.02em' }}>
              AutoApply<span style={{ color: 'var(--accent)' }}> AI</span>
            </div>
            <div style={{ font: '600 9px/1 var(--mono)', letterSpacing: '.16em', color: 'var(--text-4)', marginTop: 4 }}>
              JOB-SEARCH COPILOT
            </div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav style={{ flex: '1 1 auto', overflowY: 'auto', overflowX: 'hidden', padding: '6px 12px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {expanded && (
          <div style={{ font: '600 10px/1 var(--mono)', letterSpacing: '.15em', color: 'var(--text-4)', padding: '12px 10px 6px' }}>
            WORKSPACE
          </div>
        )}
        {nav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            title={item.label}
            aria-label={item.label}
            style={({ isActive }) => ({
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              gap: 11,
              height: 38,
              padding: expanded ? '0 10px' : 0,
              justifyContent: expanded ? 'flex-start' : 'center',
              borderRadius: 'var(--r-md)',
              textDecoration: 'none',
              cursor: 'pointer',
              font: '600 12.5px/1 var(--font)',
              color: isActive ? 'var(--accent)' : 'var(--text-3)',
              background: isActive ? 'var(--accent-soft)' : 'transparent',
              transition: 'background .15s var(--ease), color .15s var(--ease)',
            })}
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span style={{ position: 'absolute', left: 0, top: 8, bottom: 8, width: 2.5, borderRadius: 2, background: 'var(--accent)' }} />
                )}
                <span style={{ display: 'grid', placeItems: 'center', width: 18, height: 18, flex: '0 0 auto' }}>
                  <Icon name={item.icon} size={18} sw={1.85} />
                </span>
                {expanded && (
                  <span style={{ flex: '1 1 auto', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.label}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ borderTop: '1px solid var(--border)', padding: 12 }}>
        <button
          onClick={() => navigate('/applications')}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 9, padding: '9px 10px',
            borderRadius: 'var(--r-md)', background: 'var(--surface)', border: '1px solid var(--border)',
            cursor: 'pointer', textAlign: 'left', marginBottom: 10, color: 'var(--text)',
          }}
        >
          <span style={{ position: 'relative', flex: '0 0 auto', width: 9, height: 9, display: 'grid', placeItems: 'center' }}>
            <span style={{ position: 'absolute', width: 9, height: 9, borderRadius: '50%', background: 'var(--accent)', animation: 'aaPulse 1.8s var(--ease-io) infinite' }} />
            <span style={{ position: 'absolute', width: 9, height: 9, borderRadius: '50%', background: 'var(--accent)', animation: 'aaRing 1.8s var(--ease-io) infinite' }} />
          </span>
          {expanded && (
            <span style={{ flex: '1 1 auto', minWidth: 0 }}>
              <span style={{ display: 'block', font: '700 11.5px/1.2 var(--font)', color: 'var(--text)' }}>Agent active</span>
              <span style={{ display: 'block', font: '500 10.5px/1.3 var(--font)', color: 'var(--text-3)', marginTop: 2 }}>Live apply ready</span>
            </span>
          )}
          {expanded && <span style={{ color: 'var(--text-4)', flex: '0 0 auto' }}><Icon name="chevR" size={15} /></span>}
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, position: 'relative' }}>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            style={{
              flex: '1 1 auto', minWidth: 0, display: 'flex', alignItems: 'center', gap: 9, padding: '6px 7px',
              borderRadius: 'var(--r-md)', background: 'transparent', border: '1px solid transparent', cursor: 'pointer', textAlign: 'left',
            }}
          >
            <span
              style={{
                flex: '0 0 auto', width: 28, height: 28, borderRadius: '50%',
                background: 'linear-gradient(135deg,var(--accent-3),var(--interview))', display: 'grid',
                placeItems: 'center', color: '#fff', font: '700 11px/1 var(--font)',
              }}
            >
              {initials(user?.full_name, user?.email)}
            </span>
            {expanded && (
              <span style={{ flex: '1 1 auto', minWidth: 0 }}>
                <span style={{ display: 'block', font: '700 12px/1.2 var(--font)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {user?.full_name || user?.email || 'You'}
                </span>
                <span style={{ display: 'block', font: '500 10.5px/1.2 var(--font)', color: 'var(--text-3)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  Free plan · BYO key
                </span>
              </span>
            )}
          </button>

          {expanded && (
            <button
              onClick={toggleTheme}
              aria-label="Toggle theme"
              style={{
                flex: '0 0 auto', width: 32, height: 32, borderRadius: 'var(--r-md)', background: 'transparent',
                border: '1px solid var(--border)', color: 'var(--text-2)', cursor: 'pointer', display: 'grid', placeItems: 'center',
              }}
            >
              <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={16} />
            </button>
          )}

          {menuOpen && (
            <div
              role="menu"
              style={{
                position: 'absolute', bottom: 46, left: 0, width: 236, background: 'var(--surface)',
                border: '1px solid var(--border-2)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-pop)',
                padding: 6, zIndex: 60, animation: 'aaPop .16s var(--ease)',
              }}
            >
              <div style={{ padding: '10px 10px 9px', borderBottom: '1px solid var(--border)', marginBottom: 5 }}>
                <div style={{ font: '700 12.5px/1.2 var(--font)' }}>{user?.full_name || 'You'}</div>
                <div style={{ font: '500 11px/1.2 var(--mono)', color: 'var(--text-3)', marginTop: 3 }}>{user?.email}</div>
              </div>
              <MenuItem icon={theme === 'dark' ? 'sun' : 'moon'} label="Theme" hint={theme} onClick={toggleTheme} />
              <MenuItem icon="sliders" label="Density" hint={density === 'comfortable' ? 'cozy' : 'compact'} onClick={toggleDensity} />
              <MenuItem icon="sliders" label="Settings" onClick={() => { setMenuOpen(false); navigate('/settings'); }} />
              <div style={{ height: 1, background: 'var(--border)', margin: '5px 2px' }} />
              <MenuItem icon="logout" label="Sign out" danger onClick={signOut} />
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

function MenuItem({ icon, label, hint, onClick, danger }: { icon: IconName; label: string; hint?: string; onClick: () => void; danger?: boolean }) {
  return (
    <button
      role="menuitem"
      onClick={onClick}
      style={{
        width: '100%', display: 'flex', alignItems: 'center', gap: 10, padding: '8px 9px', borderRadius: 'var(--r-sm)',
        border: 0, background: 'transparent', color: danger ? 'var(--rejected)' : 'var(--text-2)', cursor: 'pointer',
        font: '600 12.5px/1 var(--font)',
      }}
    >
      <span style={{ width: 16, display: 'grid', placeItems: 'center' }}><Icon name={icon} size={15} /></span>
      <span style={{ flex: 1, textAlign: 'left' }}>{label}</span>
      {hint && <span style={{ font: '600 11px/1 var(--mono)', color: 'var(--text-4)' }}>{hint}</span>}
    </button>
  );
}
