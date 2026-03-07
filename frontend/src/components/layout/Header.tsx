import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import MenuIcon from '@mui/icons-material/Menu';
import CircleIcon from '@mui/icons-material/Circle';

import { useAppStore } from '@/store/useAppStore';
import { DRAWER_WIDTH } from './Sidebar';

function Header() {
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const wsConnected = useAppStore((s) => s.wsConnected);

  return (
    <AppBar
      position="fixed"
      color="inherit"
      elevation={0}
      sx={{
        width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
        ml: { md: `${DRAWER_WIDTH}px` },
        borderBottom: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
      }}
    >
      <Toolbar>
        <IconButton
          edge="start"
          onClick={toggleSidebar}
          sx={{ mr: 2, display: { md: 'none' } }}
          aria-label="Open navigation menu"
        >
          <MenuIcon />
        </IconButton>

        <Typography variant="h6" noWrap sx={{ flexGrow: 1 }} color="text.primary">
          {/* Page title managed by individual pages */}
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            icon={
              <CircleIcon
                sx={{
                  fontSize: 10,
                  color: wsConnected ? 'success.main' : 'error.main',
                }}
              />
            }
            label={wsConnected ? 'Connected' : 'Disconnected'}
            variant="outlined"
            size="small"
            sx={{ fontWeight: 500 }}
          />
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default Header;
