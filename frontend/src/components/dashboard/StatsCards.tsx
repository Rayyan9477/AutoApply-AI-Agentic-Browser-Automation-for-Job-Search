import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import WorkIcon from '@mui/icons-material/Work';
import SendIcon from '@mui/icons-material/Send';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import StarIcon from '@mui/icons-material/Star';

import type { DashboardStats } from '@/types/analytics';

interface StatsCardsProps {
  stats: DashboardStats | undefined;
  loading?: boolean;
}

interface StatCardItem {
  label: string;
  getValue: (s: DashboardStats) => string;
  icon: React.ReactElement;
  color: string;
}

const STAT_ITEMS: StatCardItem[] = [
  {
    label: 'Jobs Found',
    getValue: (s) => s.total_jobs_found.toLocaleString(),
    icon: <WorkIcon />,
    color: '#1976d2',
  },
  {
    label: 'Applications',
    getValue: (s) => s.total_applications.toLocaleString(),
    icon: <SendIcon />,
    color: '#00897b',
  },
  {
    label: 'Interviews',
    getValue: (s) => s.applications_interview.toLocaleString(),
    icon: <TrendingUpIcon />,
    color: '#ed6c02',
  },
  {
    label: 'Avg ATS Score',
    getValue: (s) => `${Math.round(s.avg_ats_score * 100)}%`,
    icon: <StarIcon />,
    color: '#9c27b0',
  },
];

function StatsCards({ stats, loading = false }: StatsCardsProps) {
  return (
    <Grid container spacing={3}>
      {STAT_ITEMS.map((item) => (
        <Grid item xs={12} sm={6} md={3} key={item.label}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {item.label}
                  </Typography>
                  <Typography variant="h4" fontWeight={700}>
                    {loading || !stats ? '--' : item.getValue(stats)}
                  </Typography>
                </Box>
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: 2,
                    bgcolor: `${item.color}15`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: item.color,
                  }}
                >
                  {item.icon}
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

export default StatsCards;
