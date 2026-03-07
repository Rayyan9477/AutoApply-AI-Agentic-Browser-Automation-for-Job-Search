import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

import type { ApplicationFunnelData } from '@/types/analytics';

interface ApplicationFunnelProps {
  data: ApplicationFunnelData[] | undefined;
  loading?: boolean;
}

const EMPTY_FUNNEL: ApplicationFunnelData[] = [
  { stage: 'Pending', count: 0 },
  { stage: 'Approved', count: 0 },
  { stage: 'Applied', count: 0 },
  { stage: 'Interview', count: 0 },
  { stage: 'Offer', count: 0 },
];

function ApplicationFunnel({ data, loading = false }: ApplicationFunnelProps) {
  const chartData = data && data.length > 0 ? data : EMPTY_FUNNEL;

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Application Funnel
        </Typography>

        {loading ? (
          <Box
            sx={{
              height: 300,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Typography color="text.secondary">Loading chart data...</Typography>
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="stage" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: '1px solid #e0e0e0',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                }}
              />
              <Bar dataKey="count" fill="#1976d2" radius={[4, 4, 0, 0]} maxBarSize={60} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

export default ApplicationFunnel;
