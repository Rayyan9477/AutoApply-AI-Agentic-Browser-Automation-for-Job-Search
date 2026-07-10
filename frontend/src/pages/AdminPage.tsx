import { useState } from 'react';

import Icon, { type IconName } from '@/components/ui/Icon';
import { useSystemIssues } from '@/hooks/useAdmin';
import { relativeTime } from '@/lib/status';
import type { SystemIssue } from '@/types/admin';

const card: React.CSSProperties = {
  background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-1)',
};
const TABS: { key: string; label: string; status?: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'open', label: 'Open', status: 'open' },
  { key: 'resolved', label: 'Resolved', status: 'resolved' },
];

function severityMeta(sev: string): { color: string; soft: string } {
  if (sev === 'critical') return { color: 'var(--failed)', soft: 'var(--failed-soft)' };
  if (sev === 'warning') return { color: 'var(--review)', soft: 'var(--review-soft)' };
  return { color: 'var(--text-3)', soft: 'var(--surface-2)' };
}

export default function AdminPage() {
  const [tab, setTab] = useState('all');
  const status = TABS.find((t) => t.key === tab)?.status;
  const { data, isLoading, isError } = useSystemIssues(status);
  const issues = data ?? [];

  return (
    <div style={{ animation: 'aaUp .4s var(--ease) both', maxWidth: 860 }}>
      <div style={{ marginBottom: 18 }}>
        <h1 style={{ margin: 0, font: '800 24px/1.1 var(--font)', letterSpacing: '-.03em' }}>System health</h1>
        <p style={{ margin: '6px 0 0', font: '500 13px/1.4 var(--font)', color: 'var(--text-3)' }}>Anomalies the self-monitoring harness has flagged across the platform.</p>
      </div>

      <div role="tablist" aria-label="Filter by status" style={{ display: 'flex', gap: 4, marginBottom: 14 }}>
        {TABS.map((t) => {
          const active = t.key === tab;
          return (
            <button
              key={t.key}
              role="tab"
              aria-selected={active}
              onClick={() => setTab(t.key)}
              style={{ height: 32, padding: '0 13px', borderRadius: 'var(--r-md)', border: `1px solid ${active ? 'var(--accent-line)' : 'var(--border)'}`, background: active ? 'var(--accent-soft)' : 'var(--surface-2)', color: active ? 'var(--accent)' : 'var(--text-3)', font: '600 12px/1 var(--font)', cursor: 'pointer' }}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {isError ? (
        <div style={{ ...card, ...notice }}><span style={{ color: 'var(--failed)' }}><Icon name="alert" size={16} /></span> Couldn't load system issues (superuser only).</div>
      ) : isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} style={{ ...card, height: 76, background: 'linear-gradient(90deg,var(--surface-2),var(--hover),var(--surface-2))', backgroundSize: '200% 100%', animation: 'aaShimmer 1.3s linear infinite' }} />
          ))}
        </div>
      ) : issues.length === 0 ? (
        <div style={{ ...card, ...notice, flexDirection: 'column', gap: 8, padding: '46px 20px' }}>
          <div style={{ display: 'grid', placeItems: 'center', width: 46, height: 46, borderRadius: 12, background: 'var(--applied-soft)', color: 'var(--applied)' }}><Icon name="shield" size={22} /></div>
          <div style={{ font: '700 15px/1.2 var(--font)', color: 'var(--text)' }}>All clear</div>
          <span>No system issues detected. The harness is watching.</span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {issues.map((iss) => (
            <IssueRow key={iss.id} issue={iss} />
          ))}
        </div>
      )}
    </div>
  );
}

const notice: React.CSSProperties = { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, padding: '30px 20px', color: 'var(--text-3)', font: '500 12.5px/1.4 var(--font)', textAlign: 'center' };

function IssueRow({ issue }: { issue: SystemIssue }) {
  const sm = severityMeta(issue.severity);
  const icon: IconName = issue.severity === 'critical' ? 'alert' : issue.severity === 'warning' ? 'activity' : 'server';
  return (
    <div style={{ ...card, padding: 15, display: 'flex', gap: 13, alignItems: 'flex-start' }}>
      <span style={{ flex: '0 0 auto', display: 'grid', placeItems: 'center', width: 34, height: 34, borderRadius: 9, background: sm.soft, color: sm.color }}><Icon name={icon} size={17} /></span>
      <div style={{ flex: '1 1 auto', minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ font: '700 12.5px/1 var(--mono)', color: 'var(--text)' }}>{issue.category}</span>
          <span style={{ display: 'inline-flex', alignItems: 'center', height: 20, padding: '0 8px', borderRadius: 999, background: sm.soft, color: sm.color, font: '700 10px/1 var(--mono)', letterSpacing: '.05em', textTransform: 'uppercase' }}>{issue.severity}</span>
          <span style={{ height: 20, padding: '0 8px', display: 'inline-flex', alignItems: 'center', borderRadius: 5, background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-3)', font: '600 10px/1 var(--mono)', textTransform: 'uppercase' }}>{issue.status}</span>
        </div>
        <p style={{ margin: '7px 0 0', font: '500 12.5px/1.45 var(--font)', color: 'var(--text-2)' }}>{issue.diagnosis}</p>
      </div>
      <span style={{ flex: '0 0 auto', font: '500 10.5px/1 var(--mono)', color: 'var(--text-4)', paddingTop: 3 }}>{relativeTime(issue.detected_at)}</span>
    </div>
  );
}
