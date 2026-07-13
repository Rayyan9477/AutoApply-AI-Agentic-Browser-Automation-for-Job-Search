import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import Icon from '@/components/ui/Icon';
import JobDrawer from '@/components/jobs/JobDrawer';
import { useJobs, useSearchJobs, useAnalyzeJob } from '@/hooks/useJobs';
import { useCreateApplication } from '@/hooks/useApplications';
import { useResumes, useGenerateResume } from '@/hooks/useResumes';
import { useAppStore } from '@/store/useAppStore';
import { atsColor, relativeTime } from '@/lib/status';
import type { Job, JobAnalysisResponse } from '@/types/job';

const card: React.CSSProperties = {
  background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-1)',
};

const PLATFORMS: { key: string; label: string; color: string }[] = [
  { key: 'linkedin', label: 'LinkedIn', color: 'var(--approved)' },
  { key: 'indeed', label: 'Indeed', color: 'var(--interview)' },
  { key: 'glassdoor', label: 'Glassdoor', color: 'var(--applied)' },
  { key: 'exa', label: 'Exa', color: 'var(--accent)' },
];

export default function JobSearchPage() {
  const navigate = useNavigate();
  const notify = useAppStore((s) => s.showNotification);
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [platforms, setPlatforms] = useState<Set<string>>(new Set(PLATFORMS.map((p) => p.key)));
  const { data, isLoading, isError } = useJobs(1, 30);
  const { data: resumeData } = useResumes();
  const search = useSearchJobs();
  const analyze = useAnalyzeJob();
  const createApp = useCreateApplication();
  const generate = useGenerateResume();

  const [drawerJob, setDrawerJob] = useState<Job | null>(null);
  const [analysis, setAnalysis] = useState<JobAnalysisResponse | null>(null);

  const jobs = data?.items ?? [];
  const resumes = resumeData?.items ?? [];
  const baseResumeId = resumes.find((r) => r.type === 'base')?.id ?? resumes[0]?.id ?? null;

  const openDrawer = (job: Job) => {
    setDrawerJob(job);
    setAnalysis(null);
    analyze.mutate(job.id, {
      onSuccess: (r) => setAnalysis(r),
      onError: () => notify('Could not analyze this job', 'error'),
    });
  };

  const onGenerateTailored = () => {
    if (!drawerJob || !baseResumeId) return;
    generate.mutate(
      { base_resume_id: baseResumeId, job_id: drawerJob.id },
      {
        onSuccess: () => notify(`Tailored résumé generated · ${drawerJob.title}`, 'success'),
        onError: () => notify('Could not generate the résumé', 'error'),
      },
    );
  };

  const togglePlatform = (key: string) =>
    setPlatforms((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const runSearch = () => {
    if (!query.trim()) { notify('Enter a job title or keywords to search', 'warning'); return; }
    search.mutate(
      { query: query.trim(), location: location.trim() || undefined, platforms: [...platforms] },
      {
        onSuccess: (r) => notify(`Found ${r.total} matching roles`, 'success'),
        onError: () => notify('Search failed — try again', 'error'),
      },
    );
  };

  const onAnalyze = (job: Job) =>
    analyze.mutate(job.id, {
      onSuccess: (r) => notify(`Analyzed · ${Math.round(r.match_score * 100)} ATS match`, 'success'),
      onError: () => notify('Could not analyze this job', 'error'),
    });

  const onApply = (job: Job) =>
    createApp.mutate(
      { job_id: job.id, apply_mode: 'review' },
      {
        onSuccess: () => { notify(`Queued · ${job.title}`, 'success'); navigate('/applications'); },
        onError: () => notify('Could not create the application', 'error'),
      },
    );

  return (
    <div style={{ animation: 'aaUp .4s var(--ease) both' }}>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0, font: '800 24px/1.1 var(--font)', letterSpacing: '-.03em' }}>Jobs</h1>
        <p style={{ margin: '6px 0 0', font: '500 13px/1.4 var(--font)', color: 'var(--text-3)' }}>Search across platforms and let the agent score every match against your résumé.</p>
      </div>

      {/* Search bar */}
      <form
        onSubmit={(e) => { e.preventDefault(); runSearch(); }}
        style={{ ...card, display: 'flex', gap: 10, padding: 12, marginBottom: 14, flexWrap: 'wrap' }}
      >
        <div style={{ flex: '2 1 260px', display: 'flex', alignItems: 'center', gap: 9, height: 40, padding: '0 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-3)', border: '1px solid var(--border)' }}>
          <span style={{ color: 'var(--text-3)', display: 'grid', placeItems: 'center' }}><Icon name="search" size={16} /></span>
          <input
            aria-label="Job title or keywords"
            placeholder="Job title, skills, or company"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ flex: 1, background: 'transparent', border: 0, outline: 'none', color: 'var(--text)', font: '500 13px/1 var(--font)' }}
          />
        </div>
        <div style={{ flex: '1 1 180px', display: 'flex', alignItems: 'center', gap: 9, height: 40, padding: '0 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-3)', border: '1px solid var(--border)' }}>
          <span style={{ color: 'var(--text-3)', display: 'grid', placeItems: 'center' }}><Icon name="mappin" size={16} /></span>
          <input
            aria-label="Location"
            placeholder="Location or Remote"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            style={{ flex: 1, background: 'transparent', border: 0, outline: 'none', color: 'var(--text)', font: '500 13px/1 var(--font)' }}
          />
        </div>
        <button
          type="submit"
          disabled={search.isPending}
          style={{ flex: '0 0 auto', display: 'inline-flex', alignItems: 'center', gap: 7, height: 40, padding: '0 18px', borderRadius: 'var(--r-md)', background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', font: '700 13px/1 var(--font)', cursor: 'pointer' }}
        >
          {search.isPending ? 'Searching…' : 'Search'}
        </button>
      </form>

      {/* Platform chips */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {PLATFORMS.map((p) => {
          const on = platforms.has(p.key);
          return (
            <button
              key={p.key}
              aria-pressed={on}
              onClick={() => togglePlatform(p.key)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 30, padding: '0 12px', borderRadius: 999, cursor: 'pointer', font: '600 12px/1 var(--font)', border: `1px solid ${on ? 'var(--accent-line)' : 'var(--border)'}`, background: on ? 'var(--accent-soft)' : 'var(--surface-2)', color: on ? 'var(--accent)' : 'var(--text-3)' }}
            >
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: on ? p.color : 'var(--text-4)' }} /> {p.label}
            </button>
          );
        })}
      </div>

      {/* Results grid */}
      {isError ? (
        <div style={{ ...card, ...notice }}><span style={{ color: 'var(--failed)' }}><Icon name="alert" size={16} /></span> Couldn't load jobs. Retry in a moment.</div>
      ) : isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: 14 }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} style={{ ...card, height: 150, background: 'linear-gradient(90deg,var(--surface-2),var(--hover),var(--surface-2))', backgroundSize: '200% 100%', animation: 'aaShimmer 1.3s linear infinite' }} />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div style={{ ...card, ...notice, flexDirection: 'column', gap: 8, padding: '46px 20px' }}>
          <div style={{ display: 'grid', placeItems: 'center', width: 44, height: 44, borderRadius: 12, background: 'var(--accent-soft)', color: 'var(--accent)' }}><Icon name="search" size={20} /></div>
          <div style={{ font: '700 14px/1.2 var(--font)', color: 'var(--text)' }}>No jobs yet</div>
          <span>Run a search above to discover roles across platforms.</span>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: 14 }}>
          {jobs.map((j) => (
            <JobCardView key={j.id} job={j} onOpen={() => openDrawer(j)} onAnalyze={() => onAnalyze(j)} onApply={() => onApply(j)} analyzing={analyze.isPending} applying={createApp.isPending} />
          ))}
        </div>
      )}

      {drawerJob && (
        <JobDrawer
          job={drawerJob}
          analysis={analysis}
          analyzing={analyze.isPending}
          baseResumeId={baseResumeId}
          generating={generate.isPending}
          onClose={() => setDrawerJob(null)}
          onGenerate={onGenerateTailored}
        />
      )}
    </div>
  );
}

const notice: React.CSSProperties = { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, padding: '30px 20px', color: 'var(--text-3)', font: '500 12.5px/1.4 var(--font)', textAlign: 'center' };

function ScoreRing({ score }: { score: number | null }) {
  const r = 15.5;
  const c = 2 * Math.PI * r;
  const pct = score != null ? Math.max(0, Math.min(1, score)) : 0;
  const color = score != null ? atsColor(Math.round(score * 100)) : 'var(--text-4)';
  return (
    <div style={{ position: 'relative', width: 40, height: 40, flex: '0 0 auto' }}>
      <svg width={40} height={40} viewBox="0 0 40 40" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={20} cy={20} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={3.5} />
        <circle cx={20} cy={20} r={r} fill="none" stroke={color} strokeWidth={3.5} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct)} />
      </svg>
      <span style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', font: '700 11px/1 var(--mono)', color }}>
        {score != null ? Math.round(score * 100) : '—'}
      </span>
    </div>
  );
}

function JobCardView({ job, onOpen, onAnalyze, onApply, analyzing, applying }: { job: Job; onOpen: () => void; onAnalyze: () => void; onApply: () => void; analyzing: boolean; applying: boolean }) {
  const plat = PLATFORMS.find((p) => p.key === job.platform);
  return (
    <div style={{ ...card, padding: 15, display: 'flex', flexDirection: 'column', gap: 11 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
        <ScoreRing score={job.match_score} />
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 22, padding: '0 9px', borderRadius: 999, background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-3)', font: '600 10.5px/1 var(--font)' }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: plat?.color ?? 'var(--text-4)' }} /> {plat?.label ?? job.platform}
        </span>
      </div>
      <div>
        <button onClick={onOpen} style={{ display: 'block', width: '100%', textAlign: 'left', padding: 0, margin: 0, background: 'none', border: 0, cursor: 'pointer', font: '700 14px/1.3 var(--font)', color: 'var(--text)' }}>{job.title}</button>
        <div style={{ font: '500 12px/1.3 var(--font)', color: 'var(--text-3)', marginTop: 3 }}>{job.company} · {job.location || (job.remote ? 'Remote' : '—')}</div>
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {job.remote && <Tag>Remote</Tag>}
        {job.job_type && <Tag>{job.job_type}</Tag>}
        {job.posted_date && <Tag>{relativeTime(job.posted_date)}</Tag>}
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
        {job.match_score == null && (
          <button onClick={onAnalyze} disabled={analyzing} style={btn('ghost')}>
            <Icon name="target" size={13} sw={2} /> Analyze
          </button>
        )}
        <button onClick={onApply} disabled={applying} style={btn('primary')}>
          <Icon name="check" size={13} sw={2.2} /> Apply
        </button>
      </div>
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span style={{ height: 22, padding: '0 8px', display: 'inline-flex', alignItems: 'center', borderRadius: 6, background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-3)', font: '600 10.5px/1 var(--font)' }}>{children}</span>;
}

function btn(kind: 'primary' | 'ghost'): React.CSSProperties {
  const primary = kind === 'primary';
  return {
    flex: '1 1 auto', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6, height: 32,
    padding: '0 12px', borderRadius: 'var(--r-md)', cursor: 'pointer', font: '700 12px/1 var(--font)',
    background: primary ? 'var(--accent)' : 'var(--surface-2)', border: `1px solid ${primary ? 'var(--accent)' : 'var(--border)'}`,
    color: primary ? 'var(--accent-ink)' : 'var(--text-2)',
  };
}
