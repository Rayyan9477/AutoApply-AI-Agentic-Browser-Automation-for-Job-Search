import { useEffect, useState } from 'react';

/**
 * Global connectivity banner, ported from the design's OFFLINE BANNER section.
 * Watches the browser's online/offline events and pins a status bar to the top when offline.
 */
export default function OfflineBanner() {
  const [offline, setOffline] = useState(() => typeof navigator !== 'undefined' && !navigator.onLine);

  useEffect(() => {
    const goOnline = () => setOffline(false);
    const goOffline = () => setOffline(true);
    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      role="status"
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        background: 'var(--failed)', color: '#fff', display: 'flex', alignItems: 'center',
        justifyContent: 'center', gap: 9, padding: 8, font: '700 12px/1 var(--font)',
        boxShadow: '0 6px 20px -8px rgba(0,0,0,.6)',
      }}
    >
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#fff', animation: 'aaPulse 1s infinite' }} />
      You’re offline — reconnecting to the agent…
    </div>
  );
}
