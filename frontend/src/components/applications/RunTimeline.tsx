import Icon from '@/components/ui/Icon';
import type { TimelineState, TimelineStep } from '@/lib/timeline';

const COLORS: Record<TimelineState, { line: string; fill: string }> = {
  done: { line: 'var(--applied)', fill: 'var(--applied-soft)' },
  current: { line: 'var(--accent)', fill: 'var(--accent-soft)' },
  upcoming: { line: 'var(--border-2)', fill: 'transparent' },
  failed: { line: 'var(--failed)', fill: 'var(--failed-soft)' },
  rejected: { line: 'var(--rejected)', fill: 'var(--rejected-soft)' },
  withdrawn: { line: 'var(--withdrawn)', fill: 'var(--q-soft)' },
};

function dotInner(state: TimelineState) {
  if (state === 'done') return <Icon name="check" size={13} sw={2.6} />;
  if (state === 'failed' || state === 'rejected' || state === 'withdrawn') return <Icon name="x" size={12} sw={2.4} />;
  return null;
}

/** Vertical run timeline — one node per lifecycle step, colored by state, with a failure
 *  diagnosis callout when present. Presentational: feed it `buildAppTimeline(mode, status)`. */
export function RunTimeline({ steps }: { steps: TimelineStep[] }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {steps.map((s, i) => {
        const c = COLORS[s.state];
        const last = i === steps.length - 1;
        return (
          <div key={s.key} data-step={s.key} data-state={s.state} style={{ display: 'flex', gap: 14 }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: '0 0 auto' }}>
              <span
                style={{
                  width: 26, height: 26, borderRadius: '50%', display: 'grid', placeItems: 'center',
                  border: `1px solid ${c.line}`, background: c.fill, color: c.line,
                  boxShadow: s.state === 'current' ? `0 0 0 4px ${c.fill}` : 'none',
                }}
              >
                {dotInner(s.state)}
              </span>
              {!last && <span style={{ width: 2, flex: '1 1 auto', minHeight: 22, background: 'var(--border)', margin: '4px 0' }} />}
            </div>

            <div style={{ flex: '1 1 auto', paddingBottom: last ? 0 : 18 }}>
              <div style={{ font: '700 13px/1.3 var(--font)', color: s.state === 'upcoming' ? 'var(--text-3)' : 'var(--text)' }}>{s.label}</div>
              {s.desc && <div style={{ font: '500 12px/1.4 var(--font)', color: 'var(--text-3)', marginTop: 3 }}>{s.desc}</div>}
              {s.diag && (
                <div style={{ marginTop: 8, padding: '9px 11px', borderRadius: 'var(--r-md)', background: 'var(--failed-soft)', border: '1px solid var(--failed)', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                  <span style={{ color: 'var(--failed)', flex: '0 0 auto', marginTop: 1 }}><Icon name="alert" size={14} /></span>
                  <span style={{ font: '500 12px/1.45 var(--font)', color: 'var(--text-2)' }}>{s.diag}</span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default RunTimeline;
