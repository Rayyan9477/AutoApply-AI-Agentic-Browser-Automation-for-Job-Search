import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import Icon, { type IconName } from '@/components/ui/Icon';
import { useUiStore } from '@/store/useUiStore';

interface Cmd {
  id: string;
  label: string;
  icon: IconName;
  group: 'Navigate' | 'Actions';
  run: () => void;
}
const GROUP_ORDER: Cmd['group'][] = ['Navigate', 'Actions'];

/** ⌘K command palette — fuzzy-ish command search with keyboard nav, wired to the router
 *  and UI store. Visibility is controlled by useUiStore.paletteOpen. */
export default function CommandPalette() {
  const open = useUiStore((s) => s.paletteOpen);
  const setOpen = useUiStore((s) => s.setPaletteOpen);
  const toggleTheme = useUiStore((s) => s.toggleTheme);
  const toggleDensity = useUiStore((s) => s.toggleDensity);
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const close = useCallback(() => { setOpen(false); setQuery(''); setActive(0); }, [setOpen]);
  const run = useCallback((c: Cmd) => { close(); c.run(); }, [close]);

  const commands: Cmd[] = useMemo(() => [
    { id: 'nav-dash', group: 'Navigate', label: 'Dashboard', icon: 'grid', run: () => navigate('/dashboard') },
    { id: 'nav-jobs', group: 'Navigate', label: 'Jobs', icon: 'briefcase', run: () => navigate('/jobs') },
    { id: 'nav-apps', group: 'Navigate', label: 'Applications', icon: 'inbox', run: () => navigate('/applications') },
    { id: 'nav-res', group: 'Navigate', label: 'Résumés', icon: 'file', run: () => navigate('/resumes') },
    { id: 'nav-ins', group: 'Navigate', label: 'Insights', icon: 'chart', run: () => navigate('/analytics') },
    { id: 'nav-set', group: 'Navigate', label: 'Settings', icon: 'sliders', run: () => navigate('/settings') },
    { id: 'act-search', group: 'Actions', label: 'New job search', icon: 'search', run: () => navigate('/jobs') },
    { id: 'act-theme', group: 'Actions', label: 'Toggle theme', icon: 'sun', run: toggleTheme },
    { id: 'act-density', group: 'Actions', label: 'Toggle density', icon: 'sliders', run: toggleDensity },
  ], [navigate, toggleTheme, toggleDensity]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? commands.filter((c) => c.label.toLowerCase().includes(q)) : commands;
  }, [commands, query]);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); close(); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); setActive((i) => Math.min(i + 1, visible.length - 1)); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => Math.max(i - 1, 0)); }
      else if (e.key === 'Enter') { e.preventDefault(); const c = visible[active]; if (c) run(c); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, visible, active, close, run]);

  if (!open) return null;

  const groups = GROUP_ORDER.map((label) => ({ label, items: visible.filter((c) => c.group === label) })).filter((g) => g.items.length > 0);

  return (
    <div
      onClick={close}
      role="presentation"
      style={{ position: 'fixed', inset: 0, zIndex: 100, background: 'rgba(0,0,0,.5)', backdropFilter: 'blur(2px)', display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: '12vh' }}
    >
      <div
        role="dialog"
        aria-label="Command palette"
        onClick={(e) => e.stopPropagation()}
        style={{ width: 'min(92vw,560px)', background: 'var(--surface)', border: '1px solid var(--border-2)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-pop)', overflow: 'hidden', animation: 'aaPop .16s var(--ease)' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '13px 15px', borderBottom: '1px solid var(--border)' }}>
          <Icon name="search" size={17} color="var(--text-3)" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActive(0); }}
            placeholder="Type a command or search…"
            aria-label="Command palette search"
            style={{ flex: 1, background: 'transparent', border: 0, outline: 'none', color: 'var(--text)', font: '500 14px/1 var(--font)' }}
          />
          <kbd style={{ font: '600 9.5px/16px var(--mono)', color: 'var(--text-4)', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 4, padding: '0 5px' }}>ESC</kbd>
        </div>

        <div style={{ maxHeight: 360, overflowY: 'auto', padding: 6 }}>
          {visible.length === 0 ? (
            <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-4)', font: '500 12.5px/1.4 var(--font)' }}>No commands match “{query}”.</div>
          ) : (
            groups.map((g) => (
              <div key={g.label}>
                <div style={{ font: '600 10px/1 var(--mono)', letterSpacing: '.12em', color: 'var(--text-4)', padding: '10px 10px 6px' }}>{g.label.toUpperCase()}</div>
                {g.items.map((c) => {
                  const isActive = visible[active]?.id === c.id;
                  return (
                    <button
                      key={c.id}
                      onMouseEnter={() => setActive(visible.findIndex((v) => v.id === c.id))}
                      onClick={() => run(c)}
                      style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 11, padding: '9px 10px', borderRadius: 'var(--r-md)', border: 0, background: isActive ? 'var(--hover)' : 'transparent', color: 'var(--text-2)', cursor: 'pointer', font: '600 13px/1 var(--font)', textAlign: 'left' }}
                    >
                      <span style={{ color: 'var(--text-3)', display: 'grid', placeItems: 'center', width: 18 }}><Icon name={c.icon} size={16} /></span>
                      <span style={{ flex: 1 }}>{c.label}</span>
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
