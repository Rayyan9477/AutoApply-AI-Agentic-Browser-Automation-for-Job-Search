import { useNavigate } from 'react-router-dom';

import Icon, { type IconName } from '@/components/ui/Icon';
import { useDashboardStats } from '@/hooks/useAnalytics';
import { useApplications, useApproveApplication } from '@/hooks/useApplications';
import { useAppStore } from '@/store/useAppStore';
import { useAuthStore } from '@/store/useAuthStore';
import { statusMeta, atsColor, isApprovable, relativeTime } from '@/lib/status';
import type { Application } from '@/types/application';

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

function firstName(name?: string | null, email?: string): string {
  if (name && name.trim()) return name.trim().split(/\s+/)[0] ?? name;
  return (email ?? 'there').split('@')[0] ?? 'there';
}

const card: React.CSSProperties = {
  background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-1)',
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const notify = useAppStore((s) => s.showNotification);
  const { data: stats } = useDashboardStats();
  const { data: apps, isLoading, isError } = useApplications(1, 20);
  const approve = useApproveApplication();

  const items = apps?.items ?? [];
  const live = items.find((a) => a.status === 'applying');

  const onApprove = (a: Application) => {
    approve.mutate(a.id, {
      onSuccess: () => notify(`Approved · ${a.job_title ?? 'application'}`, 'success'),
      onError: () => notify('Could not approve application', 'error'),
    });
  };

  const kpis: { label: string; value: string; icon: IconName; color: string }[] = [
    { label: 'Applications', value: fmt(stats?.total_applications), icon: 'inbox', color: 'var(--text-2)' },
    { label: 'Applied', value: fmt(stats?.applications_applied), icon: 'check', color: 'var(--applied)' },
    { label: 'Interviews', value: fmt(stats?.applications_interview), icon: 'activity', color: 'var(--interview)' },
    { label: 'Offers', value: fmt(stats?.applications_offer), icon: 'target', color: 'var(--offer)' },
    { label: 'Avg ATS', value: stats ? String(Math.round(stats.avg_ats_score)) : '—', icon: 'gauge', color: 'var(--accent)' },
    { label: 'LLM cost', value: stats ? `$${(stats.total_llm_cost_usd ?? 0).toFixed(2)}` : '—', icon: 'dollar', color: 'var(--accent)' },
  ];

  return (
    <div style={{ animation: 'aaUp .4s var(--ease) both' }}>
      {/* Greeting */}
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', marginBottom: 22 }}>
        <div>
          <h1 style={{ margin: 0, font: '800 25px/1.1 var(--font)', letterSpacing: '-.03em' }}>
            {greeting()}, {firstName(user?.full_name, user?.email)}
          </h1>
          <p style={{ margin: '7px 0 0', font: '500 13.5px/1.4 var(--font)', color: 'var(--text-3)' }}>
            Your agent applied to <span style={{ color: 'var(--applied)', fontWeight: 700 }}>{fmt(stats?.applications_applied)} roles</span> and flagged{' '}
            <span style={{ color: 'var(--review)', fontWeight: 700 }}>{fmt(stats?.applications_pending)}</span> for review.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <button
            onClick={() => navigate('/analytics')}
            style={{ display: 'flex', alignItems: 'center', gap: 7, height: 36, padding: '0 12px', borderRadius: 'var(--r-md)', background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-2)', font: '600 12.5px/1 var(--font)', cursor: 'pointer' }}
          >
            <span style={{ display: 'grid', placeItems: 'center', color: 'var(--text-3)' }}><Icon name="clock" size={15} /></span>
            Last 30 days
          </button>
          <button
            onClick={() => navigate('/jobs')}
            style={{ display: 'flex', alignItems: 'center', gap: 7, height: 36, padding: '0 14px', borderRadius: 'var(--r-md)', background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', font: '700 12.5px/1 var(--font)', cursor: 'pointer', boxShadow: '0 0 0 1px var(--accent-line),0 6px 16px -8px var(--accent-glow)' }}
          >
            <span style={{ display: 'grid', placeItems: 'center' }}><Icon name="search" size={15} sw={2} /></span>
            New search
          </button>
        </div>
      </div>

      {/* Live now — an in-flight application (agent applying right now) */}
      {live && (
        <div
          onClick={() => navigate(`/applications/${live.id}`)}
          style={{ background: 'var(--surface)', border: '1px solid var(--accent-line)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-1),inset 0 0 40px -30px var(--accent-glow)', padding: 16, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 14, cursor: 'pointer' }}
        >
          <span style={{ position: 'relative', width: 10, height: 10, flex: '0 0 auto' }}>
            <span style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: 'var(--accent)', animation: 'aaPulse 1.6s infinite' }} />
            <span style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: 'var(--accent)', animation: 'aaRing 1.6s infinite' }} />
          </span>
          <div style={{ flex: '1 1 auto', minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ font: '700 12px/1 var(--font)', color: 'var(--accent)' }}>Live now</span>
              <span style={{ font: '600 10.5px/1 var(--mono)', color: 'var(--text-4)' }}>agent applying</span>
            </div>
            <div style={{ font: '700 14px/1.3 var(--font)', marginTop: 5, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{live.job_title ?? 'Untitled role'}</div>
            <div style={{ font: '500 12px/1.3 var(--font)', color: 'var(--text-3)', marginTop: 2 }}>{live.company ?? '—'}</div>
          </div>
          {live.ats_score != null && (
            <div style={{ flex: '0 0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <span style={{ font: '800 20px/1 var(--mono)', color: atsColor(Math.round(live.ats_score)) }}>{Math.round(live.ats_score)}</span>
              <span style={{ font: '600 8px/1 var(--mono)', letterSpacing: '.1em', color: 'var(--text-4)' }}>ATS</span>
            </div>
          )}
        </div>
      )}

      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(178px,1fr))', gap: 14, marginBottom: 18 }}>
        {kpis.map((k, i) => (
          <div key={k.label} style={{ ...card, padding: '15px 15px 14px', overflow: 'hidden', animation: 'aaUp .5s var(--ease) both', animationDelay: `${i * 40}ms` }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <span style={{ font: '600 11px/1 var(--font)', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.06em' }}>{k.label}</span>
              <span style={{ display: 'grid', placeItems: 'center', color: k.color }}><Icon name={k.icon} size={16} /></span>
            </div>
            <div style={{ font: '800 27px/1 var(--font)', letterSpacing: '-.03em', color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>{k.value}</div>
          </div>
        ))}
      </div>

      {/* Pipeline table */}
      <div style={{ ...card, overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '15px 18px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ font: '700 14px/1 var(--font)', letterSpacing: '-.01em' }}>Application pipeline</span>
            <span style={{ font: '600 11px/1 var(--mono)', color: 'var(--text-4)' }}>{apps ? apps.total : ''}</span>
          </div>
          <button
            onClick={() => navigate('/applications')}
            style={{ display: 'flex', alignItems: 'center', gap: 6, height: 30, padding: '0 11px', borderRadius: 'var(--r-md)', background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-2)', font: '600 12px/1 var(--font)', cursor: 'pointer' }}
          >
            View all <Icon name="chevR" size={13} />
          </button>
        </div>

        {isError ? (
          <Notice icon="alert" text="Couldn't load your pipeline. Retry in a moment." />
        ) : isLoading ? (
          <div style={{ padding: 8 }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} style={{ height: 'var(--row-h)', margin: 4, borderRadius: 'var(--r-sm)', background: 'linear-gradient(90deg,var(--surface-2),var(--hover),var(--surface-2))', backgroundSize: '200% 100%', animation: 'aaShimmer 1.3s linear infinite' }} />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div style={{ padding: '46px 20px', textAlign: 'center' }}>
            <div style={{ display: 'inline-grid', placeItems: 'center', width: 46, height: 46, borderRadius: 12, background: 'var(--accent-soft)', color: 'var(--accent)', marginBottom: 14 }}>
              <Icon name="inbox" size={22} />
            </div>
            <div style={{ font: '700 15px/1.2 var(--font)' }}>Your pipeline is empty</div>
            <p style={{ margin: '7px 0 16px', font: '500 12.5px/1.4 var(--font)', color: 'var(--text-3)' }}>Run a search and the agent will start building your pipeline.</p>
            <button
              onClick={() => navigate('/jobs')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 34, padding: '0 14px', borderRadius: 'var(--r-md)', background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', font: '700 12.5px/1 var(--font)', cursor: 'pointer' }}
            >
              <Icon name="search" size={14} sw={2} /> Start a search
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 640 }}>
              <thead>
                <tr>
                  {['Role', 'Mode', 'Status', 'ATS', 'Applied', ''].map((h, i) => (
                    <th key={i} style={{ textAlign: i === 3 ? 'center' : 'left', font: '600 10.5px/1 var(--mono)', letterSpacing: '.08em', color: 'var(--text-4)', textTransform: 'uppercase', padding: '11px 16px', borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((a) => {
                  const sm = statusMeta(a.status);
                  return (
                    <tr
                      key={a.id}
                      onClick={() => navigate(`/applications/${a.id}`)}
                      style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                    >
                      <td style={{ padding: '0 16px', height: 'var(--row-h)' }}>
                        <div style={{ font: '700 12.5px/1.25 var(--font)', color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 260 }}>{a.job_title ?? 'Untitled role'}</div>
                        <div style={{ font: '500 11px/1.3 var(--font)', color: 'var(--text-3)', marginTop: 2 }}>{a.company ?? '—'}</div>
                      </td>
                      <td style={{ padding: '0 16px' }}>
                        <span style={{ font: '600 10.5px/1 var(--mono)', color: 'var(--text-3)', letterSpacing: '.03em', textTransform: 'uppercase' }}>{a.apply_mode}</span>
                      </td>
                      <td style={{ padding: '0 16px' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 22, padding: '0 9px', borderRadius: 999, background: sm.soft, color: sm.color, font: '700 11px/1 var(--font)' }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: sm.color }} />
                          {sm.label}
                        </span>
                      </td>
                      <td style={{ padding: '0 16px', textAlign: 'center' }}>
                        <span style={{ font: '700 12.5px/1 var(--mono)', color: a.ats_score != null ? atsColor(a.ats_score) : 'var(--text-4)' }}>
                          {a.ats_score != null ? Math.round(a.ats_score) : '—'}
                        </span>
                      </td>
                      <td style={{ padding: '0 16px' }}>
                        <span style={{ font: '500 11.5px/1 var(--mono)', color: 'var(--text-3)', whiteSpace: 'nowrap' }}>{relativeTime(a.applied_at ?? a.created_at)}</span>
                      </td>
                      <td style={{ padding: '0 16px', textAlign: 'right' }}>
                        {isApprovable(a.status) ? (
                          <button
                            onClick={(e) => { e.stopPropagation(); onApprove(a); }}
                            disabled={approve.isPending}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 28, padding: '0 11px', borderRadius: 'var(--r-md)', background: 'var(--accent-soft)', border: '1px solid var(--accent-line)', color: 'var(--accent)', font: '700 11.5px/1 var(--font)', cursor: 'pointer' }}
                          >
                            <Icon name="check" size={13} sw={2.2} /> Approve
                          </button>
                        ) : (
                          <span style={{ color: 'var(--text-4)', display: 'inline-grid', placeItems: 'center' }}><Icon name="chevR" size={15} /></span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function fmt(n: number | undefined): string {
  return n == null ? '—' : String(n);
}

function Notice({ icon, text }: { icon: IconName; text: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '30px 20px', justifyContent: 'center', color: 'var(--text-3)', font: '500 12.5px/1.4 var(--font)' }}>
      <span style={{ color: 'var(--failed)' }}><Icon name={icon} size={16} /></span>
      {text}
    </div>
  );
}
