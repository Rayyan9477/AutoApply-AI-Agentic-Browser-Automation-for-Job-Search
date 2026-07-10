import Icon, { type IconName } from '@/components/ui/Icon';
import { useApplicationFunnel, useATSDistribution, useLLMUsage, useTimeline } from '@/hooks/useAnalytics';

const card: React.CSSProperties = {
  background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-1)', padding: 18,
};

export default function AnalyticsPage() {
  const funnel = useApplicationFunnel();
  const ats = useATSDistribution();
  const llm = useLLMUsage();
  const timeline = useTimeline();

  const funnelData = funnel.data ?? [];
  const atsData = ats.data ?? [];
  const llmData = llm.data ?? [];
  const days = timeline.data ?? [];
  const funnelMax = Math.max(1, ...funnelData.map((f) => f.count));
  const atsMax = Math.max(1, ...atsData.map((b) => b.count));
  const dayMax = Math.max(1, ...days.map((d) => d.applications_applied ?? 0));

  return (
    <div style={{ animation: 'aaUp .4s var(--ease) both' }}>
      <div style={{ marginBottom: 18 }}>
        <h1 style={{ margin: 0, font: '800 24px/1.1 var(--font)', letterSpacing: '-.03em' }}>Insights</h1>
        <p style={{ margin: '6px 0 0', font: '500 13px/1.4 var(--font)', color: 'var(--text-3)' }}>How your search is converting — funnel, match quality, activity, and AI spend.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))', gap: 16 }}>
        {/* Funnel */}
        <Panel icon="filter" title="Application funnel">
          {funnelData.length === 0 ? <Empty /> : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {funnelData.map((f) => (
                <div key={f.stage} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ width: 110, flex: '0 0 auto', font: '600 12px/1.2 var(--font)', color: 'var(--text-2)' }}>{f.stage}</span>
                  <div style={{ flex: '1 1 auto', height: 10, borderRadius: 5, background: 'var(--surface-2)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${(f.count / funnelMax) * 100}%`, background: 'var(--accent)', borderRadius: 5, transition: 'width .5s var(--ease)' }} />
                  </div>
                  <span style={{ width: 34, textAlign: 'right', font: '700 12px/1 var(--mono)', color: 'var(--text)' }}>{f.count}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>

        {/* ATS distribution */}
        <Panel icon="gauge" title="ATS score distribution">
          {atsData.length === 0 ? <Empty /> : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {atsData.map((b) => (
                <div key={b.range_label} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ width: 70, flex: '0 0 auto', font: '600 11.5px/1.2 var(--mono)', color: 'var(--text-2)' }}>{b.range_label}</span>
                  <div style={{ flex: '1 1 auto', height: 10, borderRadius: 5, background: 'var(--surface-2)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${(b.count / atsMax) * 100}%`, background: 'var(--applied)', borderRadius: 5 }} />
                  </div>
                  <span style={{ width: 34, textAlign: 'right', font: '700 12px/1 var(--mono)', color: 'var(--text)' }}>{b.count}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>

        {/* Activity timeline */}
        <Panel icon="activity" title="Activity (applied / day)">
          {days.length === 0 ? <Empty /> : (
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 90 }}>
              {days.map((d) => (
                <div key={d.date} title={`${d.date}: ${d.applications_applied ?? 0}`} style={{ flex: '1 1 auto', minWidth: 3, height: `${((d.applications_applied ?? 0) / dayMax) * 100}%`, background: 'var(--accent)', borderRadius: 2, opacity: 0.85 }} />
              ))}
            </div>
          )}
        </Panel>

        {/* LLM usage */}
        <Panel icon="cpu" title="AI usage & spend">
          {llmData.length === 0 ? <Empty /> : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {llmData.map((u) => (
                <div key={`${u.provider}-${u.model}`} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                  <span style={{ flex: '1 1 auto', minWidth: 0 }}>
                    <span style={{ display: 'block', font: '700 12.5px/1.2 var(--font)', textTransform: 'capitalize' }}>{u.provider}</span>
                    <span style={{ display: 'block', font: '500 10.5px/1.2 var(--mono)', color: 'var(--text-3)', marginTop: 2 }}>{u.model} · {u.total_tokens.toLocaleString()} tok</span>
                  </span>
                  <span style={{ font: '700 12.5px/1 var(--mono)', color: 'var(--accent)' }}>${u.total_cost_usd.toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Panel({ icon, title, children }: { icon: IconName; title: string; children: React.ReactNode }) {
  return (
    <section style={card}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <span style={{ display: 'grid', placeItems: 'center', width: 30, height: 30, borderRadius: 8, background: 'var(--accent-soft)', color: 'var(--accent)' }}><Icon name={icon} size={15} /></span>
        <span style={{ font: '700 13.5px/1 var(--font)', letterSpacing: '-.01em' }}>{title}</span>
      </div>
      {children}
    </section>
  );
}

function Empty() {
  return <p style={{ margin: 0, font: '500 12px/1.4 var(--font)', color: 'var(--text-4)' }}>No data yet.</p>;
}
