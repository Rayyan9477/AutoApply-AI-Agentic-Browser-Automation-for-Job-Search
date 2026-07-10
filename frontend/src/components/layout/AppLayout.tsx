import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';

import Sidebar from './Sidebar';
import Header from './Header';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useApplicationEvents } from '@/hooks/useApplicationEvents';
import { useAppStore } from '@/store/useAppStore';

/** App shell — collapsible sidebar + header + scrollable content, per the design system.
 *  The live WebSocket + application-event wiring (unchanged) drives real-time cache updates. */
export default function AppLayout() {
  const { connected, lastMessage } = useWebSocket('/ws');
  const setWsConnected = useAppStore((s) => s.setWsConnected);

  useApplicationEvents(lastMessage);

  useEffect(() => {
    setWsConnected(connected);
  }, [connected, setWsConnected]);

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--bg)',
        color: 'var(--text)',
        fontFamily: 'var(--font)',
        letterSpacing: '-.01em',
      }}
    >
      <Sidebar />
      <div style={{ flex: '1 1 auto', minWidth: 0, display: 'flex', flexDirection: 'column', height: '100vh' }}>
        <Header />
        <main style={{ flex: '1 1 auto', minHeight: 0, overflowY: 'auto', position: 'relative' }}>
          <div style={{ maxWidth: 1460, margin: '0 auto', padding: '26px 24px 60px' }}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
