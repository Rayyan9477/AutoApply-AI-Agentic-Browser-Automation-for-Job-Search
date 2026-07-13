import { useState, type FormEvent } from 'react';

import Icon from '@/components/ui/Icon';
import { useResolveIntervention } from '@/hooks/useApplications';
import { useAppStore } from '@/store/useAppStore';

/** Global CAPTCHA/2FA intervention modal — shown when the agent hits a challenge mid-run and
 *  the worker is blocked waiting for the user's response (see the intervention rendezvous). */
export default function InterventionModal() {
  const iv = useAppStore((s) => s.pendingIntervention);
  const clear = useAppStore((s) => s.clearIntervention);
  const notify = useAppStore((s) => s.showNotification);
  const resolve = useResolveIntervention();
  const [value, setValue] = useState('');

  if (!iv) return null;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    resolve.mutate(
      { appId: iv.application_id, response: value },
      {
        onSuccess: () => { notify('Verification submitted — agent resuming', 'success'); setValue(''); clear(); },
        onError: () => notify('Could not deliver your response', 'error'),
      },
    );
  };

  const disabled = resolve.isPending || !value.trim();

  return (
    <div role="presentation" style={{ position: 'fixed', inset: 0, zIndex: 120, background: 'rgba(0,0,0,.55)', backdropFilter: 'blur(2px)', display: 'grid', placeItems: 'center', padding: 20 }}>
      <div role="dialog" aria-label="Action needed" style={{ width: 'min(94vw,440px)', background: 'var(--surface)', border: '1px solid var(--review-line)', borderRadius: 'var(--r-xl)', boxShadow: 'var(--shadow-pop)', overflow: 'hidden', animation: 'aaPop .18s var(--ease)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '16px 18px', borderBottom: '1px solid var(--border)', background: 'var(--review-soft)' }}>
          <span style={{ display: 'grid', placeItems: 'center', width: 34, height: 34, borderRadius: 9, background: 'var(--surface)', color: 'var(--review)', border: '1px solid var(--review-line)' }}><Icon name="alert" size={18} /></span>
          <span>
            <span style={{ display: 'block', font: '700 14px/1.2 var(--font)' }}>Action needed</span>
            <span style={{ display: 'block', font: '600 10.5px/1 var(--mono)', letterSpacing: '.06em', color: 'var(--review)', marginTop: 3, textTransform: 'uppercase' }}>{iv.kind}</span>
          </span>
        </div>

        <form onSubmit={submit} style={{ padding: 18 }}>
          <p style={{ margin: '0 0 14px', font: '500 12.5px/1.5 var(--font)', color: 'var(--text-2)' }}>{iv.prompt}</p>
          <label htmlFor="iv-input" style={{ display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 16 }}>
            <span style={{ font: '600 11px/1 var(--font)', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.05em' }}>Your response</span>
            <input
              id="iv-input"
              value={value}
              onChange={(e) => setValue(e.target.value.toUpperCase())}
              autoFocus
              placeholder="Enter the code shown in the browser"
              style={{ height: 42, padding: '0 12px', borderRadius: 'var(--r-md)', background: 'var(--surface-3)', border: '1px solid var(--border-2)', color: 'var(--text)', font: '600 15px/1 var(--mono)', letterSpacing: '.14em', outline: 'none' }}
            />
          </label>
          <div style={{ display: 'flex', gap: 9 }}>
            <button type="button" onClick={clear} style={{ flex: '0 0 auto', height: 40, padding: '0 14px', borderRadius: 'var(--r-md)', background: 'transparent', border: '1px solid var(--border-2)', color: 'var(--text-2)', font: '700 12.5px/1 var(--font)', cursor: 'pointer' }}>Dismiss</button>
            <button type="submit" disabled={disabled} style={{ flex: '1 1 auto', height: 40, borderRadius: 'var(--r-md)', background: 'var(--accent)', border: '1px solid var(--accent)', color: 'var(--accent-ink)', font: '700 12.5px/1 var(--font)', cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.6 : 1 }}>
              {resolve.isPending ? 'Submitting…' : 'Submit verification'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
