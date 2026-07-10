import { useEffect } from 'react';

import Icon, { type IconName } from '@/components/ui/Icon';
import { useAppStore } from '@/store/useAppStore';

type Severity = 'success' | 'error' | 'warning' | 'info';

const META: Record<Severity, { color: string; soft: string; icon: IconName }> = {
  success: { color: 'var(--applied)', soft: 'var(--applied-soft)', icon: 'check' },
  error: { color: 'var(--failed)', soft: 'var(--failed-soft)', icon: 'alert' },
  warning: { color: 'var(--review)', soft: 'var(--review-soft)', icon: 'alert' },
  info: { color: 'var(--accent)', soft: 'var(--accent-soft)', icon: 'activity' },
};

/** Global toast — design-styled replacement for the old MUI Snackbar. Reads useAppStore. */
export default function Toaster() {
  const notification = useAppStore((s) => s.notification);
  const clearNotification = useAppStore((s) => s.clearNotification);

  useEffect(() => {
    if (!notification) return;
    const t = setTimeout(clearNotification, 5400);
    return () => clearTimeout(t);
  }, [notification, clearNotification]);

  if (!notification) return null;
  const m = META[notification.severity];

  return (
    <div style={{ position: 'fixed', right: 20, bottom: 20, zIndex: 200, display: 'flex', flexDirection: 'column', gap: 10, pointerEvents: 'none' }}>
      <div
        role="status"
        style={{
          pointerEvents: 'auto', display: 'flex', alignItems: 'flex-start', gap: 11, width: 340, maxWidth: '86vw',
          padding: '13px 13px 13px 12px', background: 'var(--surface)', border: '1px solid var(--border-2)',
          borderRadius: 'var(--r-lg)', boxShadow: 'var(--shadow-pop)', animation: 'aaPop .18s var(--ease)',
        }}
      >
        <span style={{ flex: '0 0 auto', width: 30, height: 30, borderRadius: 9, display: 'grid', placeItems: 'center', background: m.soft, color: m.color }}>
          <Icon name={m.icon} size={16} sw={2} />
        </span>
        <span style={{ flex: '1 1 auto', minWidth: 0, paddingTop: 1 }}>
          <span style={{ display: 'block', font: '700 12.5px/1.35 var(--font)', color: 'var(--text)' }}>{notification.message}</span>
        </span>
        <button
          onClick={clearNotification}
          aria-label="Dismiss"
          style={{ flex: '0 0 auto', width: 22, height: 22, borderRadius: 6, border: 0, background: 'transparent', color: 'var(--text-4)', cursor: 'pointer', display: 'grid', placeItems: 'center' }}
        >
          <Icon name="x" size={14} />
        </button>
      </div>
    </div>
  );
}
