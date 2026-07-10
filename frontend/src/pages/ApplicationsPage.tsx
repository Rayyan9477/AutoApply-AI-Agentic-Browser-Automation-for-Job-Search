import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import Icon from '@/components/ui/Icon';
import { useApplications, useBulkApprove } from '@/hooks/useApplications';
import { useAppStore } from '@/store/useAppStore';
import { statusMeta, atsColor, isApprovable, relativeTime } from '@/lib/status';
import type { Application } from '@/types/application';

const card: React.CSSProperties = {
  background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-1)',
};

const TABS: { key: string; label: string; status?: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'pending_review', label: 'Needs review', status: 'pending_review' },
  { key: 'queued', label: 'Queued', status: 'queued' },
  { key: 'applied', label: 'Applied', status: 'applied' },
  { key: 'interview', label: 'Interview', status: 'interview' },
  { key: 'offer', label: 'Offer', status: 'offer' },
  { key: 'rejected', label: 'Rejected', status: 'rejected' },
];

export default function ApplicationsPage() {
  const navigate = useNavigate();
  const notify = useAppStore((s) => s.showNotification);
  const [tab, setTab] = useState('all');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const status = TABS.find((t) => t.key === tab)?.status;
  const { data, isLoading, isError } = useApplications(1, 50, status);
  const bulk = useBulkApprove();

  const items = data?.items ?? [];
  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const approveSelected = () => {
    const ids = [...selected];
    if (!ids.length) return;
    bulk.mutate(ids, {
      onSuccess: (r) => { notify(`${r.approved} approved · queued for the agent`, 'success'); setSelected(new Set()); },
      onError: () => notify('Bulk approve failed', 'error'),
    });
  };

  return (
    <div style={{ animation: 'aaUp .4s var(--ease) both' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', marginBottom: 18 }}>
        <div>
          <h1 style={{ margin: 0, font: '800 24px/1.1 var(--font)', letterSpacing: '-.03em' }}>Applications</h1>
          <p style={{ margin: '6px 0 0', font: '500 13px/1.4 var(--font)', color: 'var(--text-3)' }}>Your live pipeline — review, approve, and track every application.</p>
        </div>
      </div>

      {/* Status tabs */}
      <div role="tablist" aria-label="Filter by status" style={{ display: 'flex', gap: 4, marginBottom: 14, flexWrap: 'wrap' }}>
        {TABS.map((t) => {
          const active = t.key === tab;
          return (
            <button
              key={t.key}
              role="tab"
              aria-selected={active}
              onClick={() => { setTab(t.key); setSelected(new Set()); }}
              style={{ height: 32, padding: '0 13px', borderRadius: 'var(--r-md)', border: `1px solid ${active ? 'var(--accent-line)' : 'var(--border)'}`, background: active ? 'var(--accent-soft)' : 'var(--surface-2)', color: active ? 'var(--accent)' : 'var(--text-3)', font: '600 12px/1 var(--font)', cursor: 'pointer' }}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Bulk bar */}
      {selected.size > 0 && (
        <div style={{ ...card, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '11px 16px', marginBottom: 12, borderColor: 'var(--accent-line)', background: 'var(--accent-soft)' }}>
          <span style={{ font: '700 12.5px/1 var(--font)', color: 'var(--accent)' }}>{selected.size} selected</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setSelected(new Set())} style={{ height: 32, padding: '0 12px', borderRadius: 'var(--r-md)', background: 'transparent', border: '1px solid var(--border-2)', color: 'var(--text-2)', font: '600 12px/1 var(--font)', cursor: 'pointer' }}>Clear</button>
            <button onClick={approveSelected} disabled={bulk.isPending} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 32, padding: '0 14px', borderRadius: 'var(--r-md)', background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', font: '700 12px/1 var(--font)', cursor: 'pointer' }}>
              <Icon name="check" size={13} sw={2.2} /> Approve {selected.size}
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div style={{ ...card, overflow: 'hidden' }}>
        {isError ? (
          <Notice text="Couldn't load applications. Retry in a moment." />
        ) : isLoading ? (
          <div style={{ padding: 8 }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} style={{ height: 'var(--row-h)', margin: 4, borderRadius: 'var(--r-sm)', background: 'linear-gradient(90deg,var(--surface-2),var(--hover),var(--surface-2))', backgroundSize: '200% 100%', animation: 'aaShimmer 1.3s linear infinite' }} />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div style={{ padding: '46px 20px', textAlign: 'center', color: 'var(--text-3)' }}>
            <div style={{ display: 'inline-grid', placeItems: 'center', width: 44, height: 44, borderRadius: 12, background: 'var(--surface-2)', color: 'var(--text-4)', marginBottom: 12 }}><Icon name="inbox" size={20} /></div>
            <div style={{ font: '700 14px/1.2 var(--font)', color: 'var(--text)' }}>Nothing here yet</div>
            <p style={{ margin: '6px 0 0', font: '500 12px/1.4 var(--font)' }}>No applications match this filter.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 680 }}>
              <thead>
                <tr>
                  <th style={thStyle(false)} />
                  {['Role', 'Mode', 'Status', 'ATS', 'Applied', ''].map((h, i) => (
                    <th key={i} style={thStyle(i === 3)}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((a) => (
                  <Row key={a.id} app={a} selected={selected.has(a.id)} onToggle={() => toggle(a.id)} onOpen={() => navigate(`/applications/${a.id}`)} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function thStyle(center: boolean): React.CSSProperties {
  return { textAlign: center ? 'center' : 'left', font: '600 10.5px/1 var(--mono)', letterSpacing: '.08em', color: 'var(--text-4)', textTransform: 'uppercase', padding: '11px 16px', borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap' };
}

function Row({ app, selected, onToggle, onOpen }: { app: Application; selected: boolean; onToggle: () => void; onOpen: () => void }) {
  const sm = statusMeta(app.status);
  const approvable = isApprovable(app.status);
  return (
    <tr onClick={onOpen} style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }}>
      <td style={{ padding: '0 8px 0 16px', width: 34 }} onClick={(e) => e.stopPropagation()}>
        {approvable && (
          <input
            type="checkbox"
            aria-label={`Select ${app.job_title ?? 'application'}`}
            checked={selected}
            onChange={onToggle}
            style={{ width: 15, height: 15, accentColor: 'var(--accent)', cursor: 'pointer' }}
          />
        )}
      </td>
      <td style={{ padding: '0 16px', height: 'var(--row-h)' }}>
        <div style={{ font: '700 12.5px/1.25 var(--font)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 260 }}>{app.job_title ?? 'Untitled role'}</div>
        <div style={{ font: '500 11px/1.3 var(--font)', color: 'var(--text-3)', marginTop: 2 }}>{app.company ?? '—'}</div>
      </td>
      <td style={{ padding: '0 16px' }}>
        <span style={{ font: '600 10.5px/1 var(--mono)', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.03em' }}>{app.apply_mode}</span>
      </td>
      <td style={{ padding: '0 16px' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 22, padding: '0 9px', borderRadius: 999, background: sm.soft, color: sm.color, font: '700 11px/1 var(--font)' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: sm.color }} /> {sm.label}
        </span>
      </td>
      <td style={{ padding: '0 16px', textAlign: 'center' }}>
        <span style={{ font: '700 12.5px/1 var(--mono)', color: app.ats_score != null ? atsColor(app.ats_score) : 'var(--text-4)' }}>{app.ats_score != null ? Math.round(app.ats_score) : '—'}</span>
      </td>
      <td style={{ padding: '0 16px' }}>
        <span style={{ font: '500 11.5px/1 var(--mono)', color: 'var(--text-3)', whiteSpace: 'nowrap' }}>{relativeTime(app.applied_at ?? app.created_at)}</span>
      </td>
      <td style={{ padding: '0 16px', textAlign: 'right', color: 'var(--text-4)' }}><Icon name="chevR" size={15} /></td>
    </tr>
  );
}

function Notice({ text }: { text: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '30px 20px', justifyContent: 'center', color: 'var(--text-3)', font: '500 12.5px/1.4 var(--font)' }}>
      <span style={{ color: 'var(--failed)' }}><Icon name="alert" size={16} /></span> {text}
    </div>
  );
}
