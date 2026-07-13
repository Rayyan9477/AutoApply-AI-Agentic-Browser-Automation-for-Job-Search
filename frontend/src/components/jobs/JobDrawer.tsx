import type { ReactNode } from 'react';

import Icon from '@/components/ui/Icon';
import { atsColor, atsPercent } from '@/lib/status';
import type { Job, JobAnalysisResponse } from '@/types/job';

const PLAT_COLOR: Record<string, string> = {
  linkedin: 'var(--approved)', indeed: 'var(--interview)', glassdoor: 'var(--applied)', exa: 'var(--accent)',
};

interface JobDrawerProps {
  job: Job;
  analysis: JobAnalysisResponse | null;
  analyzing: boolean;
  baseResumeId: string | null;
  generating: boolean;
  onClose: () => void;
  onGenerate: () => void;
}

/** Right-side job-detail drawer with the match breakdown + tailor action (design §JOB DRAWER). */
export default function JobDrawer({ job, analysis, analyzing, baseResumeId, generating, onClose, onGenerate }: JobDrawerProps) {
  const paras = job.description.split(/\n\n+/).map((p) => p.trim()).filter(Boolean);
  const match = analysis ? atsPercent(analysis.match_score) : job.match_score != null ? atsPercent(job.match_score) : null;
  const canGenerate = Boolean(baseResumeId) && !generating;

  return (
    <>
      <div onClick={onClose} role="presentation" style={{ position: 'fixed', inset: 0, zIndex: 70, background: 'rgba(4,7,9,.5)', backdropFilter: 'blur(3px)', animation: 'aaPop .16s var(--ease)' }} />
      <aside role="dialog" aria-label="Job details" style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(94vw,540px)', zIndex: 71, background: 'var(--surface)', borderLeft: '1px solid var(--border-2)', boxShadow: 'var(--shadow-pop)', display: 'flex', flexDirection: 'column', fontFamily: 'var(--font)', color: 'var(--text)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '20px 22px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ flex: '1 1 auto', minWidth: 0 }}>
            <div style={{ font: '800 18px/1.2 var(--font)', letterSpacing: '-.02em' }}>{job.title}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginTop: 8, font: '500 12.5px/1 var(--font)', color: 'var(--text-3)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--text-2)' }}><Icon name="building" size={13} /> {job.company}</span>
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}><Icon name="mappin" size={13} /> {job.location || (job.remote ? 'Remote' : '—')}</span>
            </div>
            <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginTop: 10 }}>
              <span style={{ padding: '3px 8px', borderRadius: 6, background: 'var(--surface-2)', border: '1px solid var(--border)', font: '600 10.5px/1 var(--mono)', color: PLAT_COLOR[job.platform] ?? 'var(--text-3)' }}>{job.platform}</span>
              {job.remote && <Tag>Remote</Tag>}
              {job.job_type && <Tag>{job.job_type}</Tag>}
            </div>
          </div>
          <button onClick={onClose} aria-label="Close" style={{ flex: '0 0 auto', width: 32, height: 32, borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-3)', cursor: 'pointer', display: 'grid', placeItems: 'center', font: '400 18px/1 var(--font)' }}>×</button>
        </div>

        <div style={{ flex: '1 1 auto', overflowY: 'auto', padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 20 }}>
          {analyzing ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-3)', font: '500 12.5px/1 var(--font)' }}>Analyzing match…</div>
          ) : analysis ? (
            <>
              <div style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: 16, display: 'flex', alignItems: 'center', gap: 16 }}>
                <Ring pct={match ?? 0} />
                <div style={{ flex: '1 1 auto', display: 'flex', flexDirection: 'column', gap: 9 }}>
                  <Bar label="Skill match" v={atsPercent(analysis.skill_match)} />
                  <Bar label="Keyword match" v={atsPercent(analysis.keyword_match)} />
                </div>
              </div>
              {analysis.missing_skills.length > 0 && (
                <Section title="Missing keywords">
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
                    {analysis.missing_skills.map((m) => (
                      <span key={m} style={{ padding: '5px 10px', borderRadius: 7, background: 'var(--rejected-soft)', color: 'var(--rejected)', font: '600 12px/1 var(--font)' }}>{m}</span>
                    ))}
                  </div>
                </Section>
              )}
              {analysis.suggestions.length > 0 && (
                <Section title="Suggestions">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {analysis.suggestions.map((s) => (
                      <div key={s} style={{ display: 'flex', gap: 10, padding: '11px 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)' }}>
                        <span style={{ flex: '0 0 auto', color: 'var(--accent)', marginTop: 1 }}><Icon name="sparkle" size={14} /></span>
                        <span style={{ font: '500 12px/1.45 var(--font)', color: 'var(--text-2)' }}>{s}</span>
                      </div>
                    ))}
                  </div>
                </Section>
              )}
            </>
          ) : (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-3)', font: '500 12.5px/1 var(--font)' }}>No match analysis yet.</div>
          )}
          {paras.length > 0 && (
            <Section title="Description">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                {paras.map((p, i) => <p key={i} style={{ margin: 0, font: '500 12.5px/1.6 var(--font)', color: 'var(--text-2)' }}>{p}</p>)}
              </div>
            </Section>
          )}
        </div>

        <div style={{ flex: '0 0 auto', display: 'flex', gap: 9, padding: '16px 22px', borderTop: '1px solid var(--border)' }}>
          <button onClick={onGenerate} disabled={!canGenerate} title={!baseResumeId ? 'Upload a résumé first' : undefined}
            style={{ flex: '1 1 auto', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, height: 44, borderRadius: 'var(--r-md)', background: canGenerate ? 'var(--accent)' : 'var(--surface-2)', border: canGenerate ? '0' : '1px solid var(--border)', color: canGenerate ? 'var(--accent-ink)' : 'var(--text-4)', font: '700 13px/1 var(--font)', cursor: canGenerate ? 'pointer' : 'not-allowed' }}>
            <Icon name="sparkle" size={14} /> {generating ? 'Generating…' : 'Generate tailored résumé'}
          </button>
          <a href={job.url} target="_blank" rel="noreferrer" style={{ flex: '0 0 auto', display: 'flex', alignItems: 'center', gap: 7, height: 44, padding: '0 16px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-2)', font: '700 13px/1 var(--font)', textDecoration: 'none' }}>
            <Icon name="ext" size={14} /> View posting
          </a>
        </div>
      </aside>
    </>
  );
}

function Ring({ pct }: { pct: number }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const color = atsColor(pct);
  return (
    <div style={{ position: 'relative', width: 76, height: 76, flex: '0 0 auto' }}>
      <svg viewBox="0 0 76 76" style={{ width: 76, height: 76, transform: 'rotate(-90deg)' }}>
        <circle cx={38} cy={38} r={r} fill="none" stroke="var(--surface-3)" strokeWidth={6} />
        <circle cx={38} cy={38} r={r} fill="none" stroke={color} strokeWidth={6} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct / 100)} />
      </svg>
      <span style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ font: '800 20px/1 var(--mono)', color }}>{pct}</span>
        <span style={{ font: '600 8px/1 var(--mono)', color: 'var(--text-4)', marginTop: 2 }}>MATCH</span>
      </span>
    </div>
  );
}

function Bar({ label, v }: { label: string; v: number }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={{ font: '600 11px/1 var(--font)', color: 'var(--text-2)' }}>{label}</span>
        <span style={{ font: '700 11px/1 var(--mono)', color: 'var(--text)' }}>{v}</span>
      </div>
      <div style={{ height: 5, borderRadius: 3, background: 'var(--surface-3)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${v}%`, background: atsColor(v), borderRadius: 3 }} />
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <div style={{ font: '700 12.5px/1 var(--font)', marginBottom: 9 }}>{title}</div>
      {children}
    </div>
  );
}

function Tag({ children }: { children: ReactNode }) {
  return <span style={{ padding: '3px 8px', borderRadius: 6, background: 'var(--surface-2)', border: '1px solid var(--border)', font: '600 11px/1 var(--font)', color: 'var(--text-3)' }}>{children}</span>;
}
