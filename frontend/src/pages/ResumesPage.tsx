import { useState } from 'react';

import Icon from '@/components/ui/Icon';
import ResumeCard from '@/components/resumes/ResumeCard';
import ResumePreviewPanel from '@/components/resumes/ResumePreviewPanel';
import { useResumes, useUploadResume, useOptimizeResume, useGenerateResume, useScoreResume } from '@/hooks/useResumes';
import { useJobs } from '@/hooks/useJobs';
import { downloadResumeFile } from '@/services/resumeService';
import { useAppStore } from '@/store/useAppStore';
import type { Resume, ResumeScoreResponse } from '@/types/resume';

const card: React.CSSProperties = {
  background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-1)',
};
const notice: React.CSSProperties = { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, padding: '30px 20px', color: 'var(--text-3)', font: '500 12.5px/1.4 var(--font)', textAlign: 'center' };

export default function ResumesPage() {
  const notify = useAppStore((s) => s.showNotification);
  const { data, isLoading, isError } = useResumes();
  const { data: jobData } = useJobs(1, 50);
  const upload = useUploadResume();
  const optimize = useOptimizeResume();
  const generate = useGenerateResume();
  const score = useScoreResume();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [targetJobId, setTargetJobId] = useState('');
  const [scoreResult, setScoreResult] = useState<ResumeScoreResponse | null>(null);

  const resumes = data?.items ?? [];
  const jobs = jobData?.items ?? [];
  const selected = resumes.find((r) => r.id === selectedId) ?? resumes[0] ?? null;
  const baseResumeId = resumes.find((r) => r.type === 'base')?.id ?? resumes[0]?.id ?? null;

  const onUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    upload.mutate(file, {
      onSuccess: () => notify(`Uploaded · ${file.name}`, 'success'),
      onError: () => notify('Upload failed — supported: PDF, DOCX', 'error'),
    });
    e.target.value = '';
  };

  const onSelect = (r: Resume) => { setSelectedId(r.id); setScoreResult(null); };

  const onOptimize = (r: Resume) =>
    optimize.mutate(r.id, {
      onSuccess: () => notify(`Optimized · ${r.name}`, 'success'),
      onError: () => notify('Could not optimize this résumé', 'error'),
    });

  const onDownload = async (r: Resume, format: 'pdf' | 'docx') => {
    try {
      await downloadResumeFile(r.id, format, r.name);
    } catch {
      notify('Could not download the résumé', 'error');
    }
  };

  const onScore = () => {
    if (!selected || !targetJobId) return;
    score.mutate(
      { resumeId: selected.id, jobId: targetJobId },
      {
        onSuccess: (res) => { setScoreResult(res); notify('Scored against the selected job', 'success'); },
        onError: () => notify('Could not score this résumé', 'error'),
      },
    );
  };

  const onGenerate = () => {
    if (!baseResumeId || !targetJobId) { notify('Pick a target job (in the panel) first', 'warning'); return; }
    generate.mutate(
      { base_resume_id: baseResumeId, job_id: targetJobId },
      {
        onSuccess: () => notify('Tailored résumé generated', 'success'),
        onError: () => notify('Could not generate the résumé', 'error'),
      },
    );
  };

  const canGenerate = Boolean(baseResumeId) && Boolean(targetJobId) && !generate.isPending;

  return (
    <div style={{ animation: 'aaUp .4s var(--ease) both' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', marginBottom: 18 }}>
        <div>
          <h1 style={{ margin: 0, font: '800 24px/1.1 var(--font)', letterSpacing: '-.03em' }}>Résumés</h1>
          <p style={{ margin: '6px 0 0', font: '500 13px/1.4 var(--font)', color: 'var(--text-3)' }}>Your base résumé plus every tailored and optimized variant the agent has generated.</p>
        </div>
        <button
          onClick={onGenerate}
          disabled={!canGenerate}
          title={!baseResumeId ? 'Upload a base résumé first' : !targetJobId ? 'Pick a target job in the panel' : undefined}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 7, height: 36, padding: '0 14px', borderRadius: 'var(--r-md)', background: canGenerate ? 'var(--accent)' : 'var(--surface-2)', border: canGenerate ? '1px solid var(--accent)' : '1px solid var(--border)', color: canGenerate ? 'var(--accent-ink)' : 'var(--text-4)', font: '700 12.5px/1 var(--font)', cursor: canGenerate ? 'pointer' : 'not-allowed' }}
        >
          <Icon name="sparkle" size={14} /> {generate.isPending ? 'Generating…' : 'Generate tailored'}
        </button>
      </div>

      {isError ? (
        <div style={{ ...card, ...notice }}><span style={{ color: 'var(--failed)' }}><Icon name="alert" size={16} /></span> Couldn't load your résumés.</div>
      ) : isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(206px,1fr))', gap: 14 }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} style={{ ...card, height: 200, background: 'linear-gradient(90deg,var(--surface-2),var(--hover),var(--surface-2))', backgroundSize: '200% 100%', animation: 'aaShimmer 1.3s linear infinite' }} />
          ))}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 336px', gap: 16, alignItems: 'start' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, minWidth: 0 }}>
            {/* Upload dropzone */}
            <label style={{ ...card, border: '1px dashed var(--border-2)', padding: 22, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 11, cursor: 'pointer' }}>
              <span style={{ width: 46, height: 46, borderRadius: 12, background: 'var(--accent-soft)', border: '1px solid var(--accent-line)', display: 'grid', placeItems: 'center', color: 'var(--accent)' }}><Icon name="upload" size={20} /></span>
              <span>
                <span style={{ display: 'block', font: '700 13.5px/1.2 var(--font)', color: 'var(--text)' }}>Drag &amp; drop a résumé</span>
                <span style={{ display: 'block', font: '500 12px/1.4 var(--font)', color: 'var(--text-3)', marginTop: 4 }}>PDF or DOCX · we parse skills and sections automatically</span>
              </span>
              <span style={{ height: 34, padding: '0 16px', display: 'inline-flex', alignItems: 'center', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)', font: '700 12px/1 var(--font)' }}>{upload.isPending ? 'Uploading…' : 'Browse files'}</span>
              <input type="file" accept=".pdf,.docx,.doc" aria-label="Upload résumé" onChange={onUpload} style={{ position: 'absolute', width: 1, height: 1, opacity: 0 }} />
            </label>

            {resumes.length === 0 ? (
              <div style={{ ...card, ...notice, flexDirection: 'column', gap: 8, padding: '40px 20px' }}>
                <div style={{ display: 'grid', placeItems: 'center', width: 44, height: 44, borderRadius: 12, background: 'var(--accent-soft)', color: 'var(--accent)' }}><Icon name="file" size={20} /></div>
                <div style={{ font: '700 14px/1.2 var(--font)', color: 'var(--text)' }}>No résumés yet</div>
                <span>Upload a PDF or DOCX to get started.</span>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ font: '700 13px/1 var(--font)' }}>Your résumés</span>
                  <span style={{ font: '600 11px/1 var(--mono)', color: 'var(--text-4)' }}>{resumes.length} {resumes.length === 1 ? 'VARIANT' : 'VARIANTS'}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(206px,1fr))', gap: 14 }}>
                  {resumes.map((r) => (
                    <ResumeCard
                      key={r.id}
                      resume={r}
                      jobLabel={jobs.find((j) => j.id === r.job_id)?.title}
                      selected={selected?.id === r.id}
                      onSelect={() => onSelect(r)}
                      onOptimize={() => onOptimize(r)}
                      onDownload={() => onDownload(r, r.has_pdf ? 'pdf' : 'docx')}
                      optimizing={optimize.isPending}
                    />
                  ))}
                </div>
              </>
            )}
          </div>

          {selected && (
            <ResumePreviewPanel
              resume={selected}
              score={scoreResult}
              scoring={score.isPending}
              jobs={jobs}
              targetJobId={targetJobId}
              onSelectJob={setTargetJobId}
              onScore={onScore}
              onDownload={(fmt) => onDownload(selected, fmt)}
            />
          )}
        </div>
      )}
    </div>
  );
}
