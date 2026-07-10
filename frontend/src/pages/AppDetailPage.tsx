import { useParams, useNavigate } from 'react-router-dom';

import Icon from '@/components/ui/Icon';
import RunTimeline from '@/components/applications/RunTimeline';
import { useApplication, useUpdateApplicationStatus } from '@/hooks/useApplications';
import { useAppStore } from '@/store/useAppStore';
import { buildAppTimeline } from '@/lib/timeline';
import { statusMeta, atsColor, relativeTime } from '@/lib/status';

const card: React.CSSProperties = {
  background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-1)',
};
const ACTIVE = new Set(['queued', 'pending_review', 'approved', 'applying']);

export default function AppDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const notify = useAppStore((s) => s.showNotification);
  const { data: app, isLoading, isError } = useApplication(id);
  const updateStatus = useUpdateApplicationStatus();

  const setStatus = (status: string, msg: string) =>
    app &&
    updateStatus.mutate(
      { appId: app.id, update: { status } },
      { onSuccess: () => notify(msg, 'success'), onError: () => notify('Could not update status', 'error') },
    );

  return (
    <div style={{ animation: 'aaUp .4s var(--ease) both', maxWidth: 860 }}>
      <button
        onClick={() => navigate('/applications')}
        style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 30, padding: '0 10px 0 8px', marginBottom: 16, borderRadius: 'var(--r-md)', background: 'transparent', border: '1px solid transparent', color: 'var(--text-3)', font: '600 12.5px/1 var(--font)', cursor: 'pointer' }}
      >
        <Icon name="chevL" size={15} /> Applications
      </button>

      {isLoading ? (
        <div style={{ ...card, height: 160, background: 'linear-gradient(90deg,var(--surface-2),var(--hover),var(--surface-2))', backgroundSize: '200% 100%', animation: 'aaShimmer 1.3s linear infinite' }} />
      ) : isError || !app ? (
        <div style={{ ...card, padding: '40px 20px', textAlign: 'center', color: 'var(--text-3)' }}>
          <div style={{ display: 'inline-grid', placeItems: 'center', width: 44, height: 44, borderRadius: 12, background: 'var(--failed-soft)', color: 'var(--failed)', marginBottom: 12 }}>
            <Icon name="alert" size={20} />
          </div>
          <div style={{ font: '700 15px/1.2 var(--font)', color: 'var(--text)' }}>Application not found</div>
          <p style={{ margin: '6px 0 0', font: '500 12.5px/1.4 var(--font)' }}>It may have been removed, or the link is stale.</p>
        </div>
      ) : (
        (() => {
          const sm = statusMeta(app.status);
          const steps = buildAppTimeline(app.apply_mode, app.status);
          return (
            <>
              {/* Header */}
              <div style={{ ...card, padding: 20, marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                      <h1 style={{ margin: 0, font: '800 21px/1.2 var(--font)', letterSpacing: '-.02em' }}>{app.job_title ?? 'Untitled role'}</h1>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 24, padding: '0 10px', borderRadius: 999, background: sm.soft, color: sm.color, font: '700 11.5px/1 var(--font)' }}>
                        <span style={{ width: 6, height: 6, borderRadius: '50%', background: sm.color }} />
                        {sm.label}
                      </span>
                    </div>
                    <p style={{ margin: '7px 0 0', font: '500 13px/1.4 var(--font)', color: 'var(--text-3)' }}>
                      {app.company ?? '—'} · {app.apply_mode} mode · {app.applied_at ? `applied ${relativeTime(app.applied_at)}` : `created ${relativeTime(app.created_at)}`}
                    </p>
                  </div>
                  {app.ats_score != null && (
                    <div style={{ flex: '0 0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
                      <span style={{ font: '800 24px/1 var(--mono)', color: atsColor(app.ats_score) }}>{Math.round(app.ats_score)}</span>
                      <span style={{ font: '600 9px/1 var(--mono)', letterSpacing: '.1em', color: 'var(--text-4)' }}>ATS</span>
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', gap: 9, marginTop: 16, flexWrap: 'wrap' }}>
                  {app.status === 'failed' && (
                    <ActionButton icon="refresh" label="Re-run" primary disabled={updateStatus.isPending} onClick={() => setStatus('queued', 'Re-queued — the agent will retry')} />
                  )}
                  {ACTIVE.has(app.status) && (
                    <ActionButton icon="x" label="Withdraw" danger disabled={updateStatus.isPending} onClick={() => setStatus('withdrawn', 'Application withdrawn')} />
                  )}
                  <ActionButton icon="briefcase" label="View job" onClick={() => navigate('/jobs')} />
                </div>
              </div>

              {/* Timeline */}
              <div style={{ ...card, padding: 20 }}>
                <div style={{ font: '700 14px/1 var(--font)', letterSpacing: '-.01em', marginBottom: 16 }}>Run timeline</div>
                <RunTimeline steps={steps} />
              </div>

              {app.notes && (
                <div style={{ ...card, padding: 18, marginTop: 16 }}>
                  <div style={{ font: '700 13px/1 var(--font)', marginBottom: 8 }}>Notes</div>
                  <p style={{ margin: 0, font: '500 12.5px/1.5 var(--font)', color: 'var(--text-2)' }}>{app.notes}</p>
                </div>
              )}
            </>
          );
        })()
      )}
    </div>
  );
}

function ActionButton({ icon, label, onClick, primary, danger, disabled }: { icon: 'refresh' | 'x' | 'briefcase'; label: string; onClick: () => void; primary?: boolean; danger?: boolean; disabled?: boolean }) {
  const bg = primary ? 'var(--accent)' : danger ? 'var(--rejected-soft)' : 'var(--surface-2)';
  const color = primary ? 'var(--accent-ink)' : danger ? 'var(--rejected)' : 'var(--text-2)';
  const border = primary ? 'var(--accent)' : danger ? 'var(--rejected)' : 'var(--border)';
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 34, padding: '0 13px', borderRadius: 'var(--r-md)', background: bg, border: `1px solid ${border}`, color, font: '700 12px/1 var(--font)', cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.6 : 1 }}
    >
      <Icon name={icon} size={14} sw={2} /> {label}
    </button>
  );
}
