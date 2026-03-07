import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Chip from '@mui/material/Chip';

import StatsCards from '@/components/dashboard/StatsCards';
import ApplicationFunnel from '@/components/dashboard/ApplicationFunnel';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { useDashboardStats, useApplicationFunnel } from '@/hooks/useAnalytics';
import { useApplications } from '@/hooks/useApplications';

function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: funnel, isLoading: funnelLoading } = useApplicationFunnel();
  const { data: recentApps } = useApplications(1, 5);

  return (
    <ErrorBoundary>
      <Box>
        <Typography variant="h4" gutterBottom>
          Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Overview of your job application pipeline
        </Typography>

        <StatsCards stats={stats} loading={statsLoading} />

        <Grid container spacing={3} sx={{ mt: 1 }}>
          <Grid item xs={12} md={8}>
            <ApplicationFunnel data={funnel} loading={funnelLoading} />
          </Grid>

          <Grid item xs={12} md={4}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Recent Applications
                </Typography>

                {recentApps && recentApps.items.length > 0 ? (
                  <List disablePadding>
                    {recentApps.items.map((app) => (
                      <ListItem key={app.id} disablePadding sx={{ mb: 1 }}>
                        <ListItemText
                          primary={`Application #${app.id.slice(0, 8)}`}
                          secondary={new Date(app.created_at).toLocaleDateString()}
                          primaryTypographyProps={{ variant: 'body2', fontWeight: 500 }}
                          secondaryTypographyProps={{ variant: 'caption' }}
                        />
                        <Chip label={app.status} size="small" variant="outlined" />
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Box
                    sx={{
                      textAlign: 'center',
                      py: 4,
                    }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      No applications yet. Start by searching for jobs.
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    </ErrorBoundary>
  );
}

export default DashboardPage;
