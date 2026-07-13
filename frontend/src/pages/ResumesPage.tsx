import { useRef } from 'react';

import Icon from '@/components/ui/Icon';
import { useResumes, useUploadResume, useOptimizeResume } from '@/hooks/useResumes';
import { useAppStore } from '@/store/useAppStore';
import { atsColor, atsPercent, relativeTime } from '@/lib/status';
import type { Resume } from '@/types/resume';

const card: React.CSSProperties = {
  background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-1)',
};

export default function ResumesPage() {
  const notify = useAppStore((s) => s.showNotification);
  const fileRef = useRef<HTMLInputElement>(null);
  const { data, isLoading, isError } = useResumes();
  const upload = useUploadResume();
  const optimize = useOptimizeResume();

  const resumes = data?.items ?? [];

  const onUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    upload.mutate(file, {
      onSuccess: () => notify(`Uploaded · ${file.name}`, 'success'),
      onError: () => notify('Upload failed — supported: PDF, DOCX', 'error'),
    });
    e.target.value = '';
  };

  const onOptimize = (r: Resume) =>
    optimize.mutate(r.id, {
      onSuccess: () => notify(`Optimized · ${r.name}`, 'success'),
      onError: () => notify('Could not optimize this résumé', 'error'),
    });

  return (
    <div style={{ animation: 'aaUp .4s var(--ease) both' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', marginBottom: 18 }}>
        <div>
          <h1 style={{ margin: 0, font: '800 24px/1.1 var(--font)', letterSpacing: '-.03em' }}>Résumés</h1>
          <p style={{ margin: '6px 0 0', font: '500 13px/1.4 var(--font)', color: 'var(--text-3)' }}>Upload a base résumé; the agent tailors and ATS-optimizes it per role.</p>
        </div>
        <label
          style={{ display: 'inline-flex', alignItems: 'center', gap: 8, height: 38, padding: '0 15px', borderRadius: 'var(--r-md)', background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', font: '700 12.5px/1 var(--font)', cursor: 'pointer' }}
        >
          <Icon name="upload" size={15} sw={2} /> {upload.isPending ? 'Uploading…' : 'Upload résumé'}
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.doc"
            aria-label="Upload résumé"
            onChange={onUpload}
            style={{ position: 'absolute', width: 1, height: 1, opacity: 0 }}
          />
        </label>
      </div>

      {isError ? (
        <div style={{ ...card, ...notice }}><span style={{ color: 'var(--failed)' }}><Icon name="alert" size={16} /></span> Couldn't load your résumés.</div>
      ) : isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: 14 }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} style={{ ...card, height: 132, background: 'linear-gradient(90deg,var(--surface-2),var(--hover),var(--surface-2))', backgroundSize: '200% 100%', animation: 'aaShimmer 1.3s linear infinite' }} />
          ))}
        </div>
      ) : resumes.length === 0 ? (
        <div style={{ ...card, ...notice, flexDirection: 'column', gap: 8, padding: '46px 20px' }}>
          <div style={{ display: 'grid', placeItems: 'center', width: 44, height: 44, borderRadius: 12, background: 'var(--accent-soft)', color: 'var(--accent)' }}><Icon name="file" size={20} /></div>
          <div style={{ font: '700 14px/1.2 var(--font)', color: 'var(--text)' }}>No résumés yet</div>
          <span>Upload a PDF or DOCX to get started.</span>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(300px,1fr))', gap: 14 }}>
          {resumes.map((r) => (
            <ResumeCard key={r.id} resume={r} onOptimize={() => onOptimize(r)} optimizing={optimize.isPending} />
          ))}
        </div>
      )}
    </div>
  );
}

const notice: React.CSSProperties = { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, padding: '30px 20px', color: 'var(--text-3)', font: '500 12.5px/1.4 var(--font)', textAlign: 'center' };

function ResumeCard({ resume, onOptimize, optimizing }: { resume: Resume; onOptimize: () => void; optimizing: boolean }) {
  const tailored = resume.type === 'tailored';
  return (
    <div style={{ ...card, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
        <span style={{ display: 'grid', placeItems: 'center', width: 34, height: 34, borderRadius: 9, background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-2)' }}><Icon name="file" size={17} /></span>
        {resume.ats_score != null && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <span style={{ font: '800 17px/1 var(--mono)', color: atsColor(atsPercent(resume.ats_score)) }}>{atsPercent(resume.ats_score)}</span>
            <span style={{ font: '600 8px/1 var(--mono)', letterSpacing: '.1em', color: 'var(--text-4)' }}>ATS</span>
          </div>
        )}
      </div>
      <div>
        <div style={{ font: '700 13.5px/1.3 var(--font)', color: 'var(--text)' }}>{resume.name}</div>
        <div style={{ display: 'flex', gap: 6, marginTop: 7, flexWrap: 'wrap' }}>
          <span style={{ height: 20, padding: '0 8px', display: 'inline-flex', alignItems: 'center', borderRadius: 5, font: '700 9.5px/1 var(--mono)', letterSpacing: '.04em', textTransform: 'uppercase', background: tailored ? 'var(--interview-soft)' : 'var(--surface-2)', color: tailored ? 'var(--interview)' : 'var(--text-3)' }}>{tailored ? 'Tailored' : 'Base'}</span>
          {resume.has_pdf && <Fmt>PDF</Fmt>}
          {resume.has_docx && <Fmt>DOCX</Fmt>}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={{ font: '500 10.5px/1 var(--mono)', color: 'var(--text-4)' }}>{relativeTime(resume.created_at)}</span>
        <button
          onClick={onOptimize}
          disabled={optimizing}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 30, padding: '0 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-2)', font: '700 11.5px/1 var(--font)', cursor: 'pointer' }}
        >
          <Icon name="sparkle" size={13} /> Optimize
        </button>
      </div>
    </div>
  );
}

function Fmt({ children }: { children: React.ReactNode }) {
  return <span style={{ height: 20, padding: '0 7px', display: 'inline-flex', alignItems: 'center', borderRadius: 5, background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-4)', font: '600 9.5px/1 var(--mono)' }}>{children}</span>;
}
