import Icon from '@/components/ui/Icon';
import { atsColor, atsPercent, relativeTime } from '@/lib/status';
import type { Resume } from '@/types/resume';

const TYPE_META: Record<string, { label: string; color: string; soft: string }> = {
  base: { label: 'Base', color: 'var(--text-3)', soft: 'var(--surface-2)' },
  tailored: { label: 'Tailored', color: 'var(--interview)', soft: 'var(--interview-soft)' },
  optimized: { label: 'Optimized', color: 'var(--offer)', soft: 'var(--offer-soft)' },
};

interface ResumeCardProps {
  resume: Resume;
  jobLabel?: string;
  selected: boolean;
  onSelect: () => void;
  onOptimize: () => void;
  onDownload: () => void;
  optimizing: boolean;
}

/** A résumé tile: thumbnail + type badge + ATS + optimize / download (design §RÉSUMÉS card). */
export default function ResumeCard({ resume, jobLabel, selected, onSelect, onOptimize, onDownload, optimizing }: ResumeCardProps) {
  const t = TYPE_META[resume.type] ?? TYPE_META['base']!;
  const canDownload = resume.has_pdf || resume.has_docx;
  const iconBtn: React.CSSProperties = {
    width: 28, height: 28, borderRadius: 7, background: 'var(--surface-2)', border: '1px solid var(--border)',
    color: 'var(--text-3)', cursor: 'pointer', display: 'grid', placeItems: 'center',
  };
  return (
    <div style={{ background: 'var(--surface)', border: `1px solid ${selected ? 'var(--accent-line)' : 'var(--border)'}`, borderRadius: 'var(--r-lg)', boxShadow: selected ? '0 0 0 1px var(--accent-line)' : 'var(--shadow-1)', padding: 12, display: 'flex', flexDirection: 'column', gap: 11 }}>
      <button
        onClick={onSelect}
        aria-label={`Select résumé ${resume.name}`}
        style={{ display: 'block', width: '100%', textAlign: 'left', padding: 0, margin: 0, background: 'none', border: 0, cursor: 'pointer', color: 'inherit' }}
      >
        <div style={{ height: 116, borderRadius: 'var(--r-md)', background: 'repeating-linear-gradient(135deg,var(--surface-2),var(--surface-2) 7px,var(--surface-3) 7px,var(--surface-3) 14px)', border: '1px solid var(--border)', display: 'grid', placeItems: 'center', position: 'relative' }}>
          <span style={{ position: 'absolute', top: 8, left: 8, padding: '3px 7px', borderRadius: 6, background: t.soft, color: t.color, font: '700 9px/1 var(--mono)', letterSpacing: '.04em', textTransform: 'uppercase' }}>{t.label}</span>
          <span style={{ font: '600 10px/1 var(--mono)', color: 'var(--text-4)' }}>{resume.template_id}</span>
        </div>
        <div style={{ marginTop: 10 }}>
          <div style={{ font: '700 12.5px/1.25 var(--font)', color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{resume.name}</div>
          <div style={{ font: '500 11px/1.3 var(--font)', color: 'var(--text-3)', marginTop: 3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{jobLabel || 'Base résumé'} · {relativeTime(resume.created_at)}</div>
        </div>
      </button>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: 10 }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, font: '700 12px/1 var(--mono)', color: resume.ats_score != null ? atsColor(atsPercent(resume.ats_score)) : 'var(--text-4)' }}>
          {resume.ats_score != null ? atsPercent(resume.ats_score) : '—'}
          <span style={{ font: '600 9px/1 var(--mono)', color: 'var(--text-4)' }}>ATS</span>
        </span>
        <span style={{ display: 'flex', gap: 5 }}>
          <button onClick={onOptimize} disabled={optimizing} aria-label={`Optimize résumé ${resume.name}`} style={iconBtn}><Icon name="wand" size={14} /></button>
          <button onClick={onDownload} disabled={!canDownload} aria-label={`Download résumé ${resume.name}`} style={{ ...iconBtn, cursor: canDownload ? 'pointer' : 'not-allowed', color: canDownload ? 'var(--text-3)' : 'var(--text-4)' }}><Icon name="download" size={14} /></button>
        </span>
      </div>
    </div>
  );
}
