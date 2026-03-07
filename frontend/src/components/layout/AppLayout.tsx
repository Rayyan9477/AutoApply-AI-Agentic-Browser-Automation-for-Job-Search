import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Box from '@mui/material/Box';
import Toolbar from '@mui/material/Toolbar';

import Sidebar, { DRAWER_WIDTH } from './Sidebar';
import Header from './Header';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAppStore } from '@/store/useAppStore';

function AppLayout() {
  const { connected } = useWebSocket('/ws');
  const setWsConnected = useAppStore((s) => s.setWsConnected);

  useEffect(() => {
    setWsConnected(connected);
  }, [connected, setWsConnected]);

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Header />
      <Sidebar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          bgcolor: 'background.default',
          minHeight: '100vh',
        }}
      >
        <Toolbar />
        <Box sx={{ p: 3 }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}

export default AppLayout;
