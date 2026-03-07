import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

import ApplicationFunnel from '@/components/dashboard/ApplicationFunnel';
import LoadingState from '@/components/common/LoadingState';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import {
  useApplicationFunnel,
  useATSDistribution,
  useLLMUsage,
  useTimeline,
} from '@/hooks/useAnalytics';

function AnalyticsPage() {
  const { data: funnel, isLoading: funnelLoading } = useApplicationFunnel();
  const { data: atsDistribution, isLoading: atsLoading } = useATSDistribution();
  const { data: llmUsage, isLoading: llmLoading } = useLLMUsage();
  const { data: timeline, isLoading: timelineLoading } = useTimeline();

  const isLoading = funnelLoading || atsLoading || llmLoading || timelineLoading;

  if (isLoading) {
    return <LoadingState message="Loading analytics..." />;
  }

  return (
    <ErrorBoundary>
      <Box>
        <Typography variant="h4" gutterBottom>
          Analytics
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Detailed insights into your job search performance
        </Typography>

        <Grid container spacing={3}>
          {/* Activity Timeline */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Activity Timeline
                </Typography>
                {timeline && timeline.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={timeline} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                      <Tooltip
                        contentStyle={{
                          borderRadius: 8,
                          border: '1px solid #e0e0e0',
                        }}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="jobs_found"
                        stroke="#1976d2"
                        strokeWidth={2}
                        name="Jobs Found"
                      />
                      <Line
                        type="monotone"
                        dataKey="applications_created"
                        stroke="#00897b"
                        strokeWidth={2}
                        name="Apps Created"
                      />
                      <Line
                        type="monotone"
                        dataKey="applications_applied"
                        stroke="#ed6c02"
                        strokeWidth={2}
                        name="Apps Applied"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <Typography color="text.secondary">
                      No timeline data available yet. Start applying to see activity trends.
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Application Funnel */}
          <Grid item xs={12} md={6}>
            <ApplicationFunnel data={funnel} />
          </Grid>

          {/* ATS Score Distribution */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  ATS Score Distribution
                </Typography>
                {atsDistribution && atsDistribution.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={atsDistribution}
                      margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="range_label" tick={{ fontSize: 11 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                      <Tooltip
                        contentStyle={{
                          borderRadius: 8,
                          border: '1px solid #e0e0e0',
                        }}
                      />
                      <Bar dataKey="count" fill="#00897b" radius={[4, 4, 0, 0]} maxBarSize={50} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <Typography color="text.secondary">
                      No ATS score data available yet.
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* LLM Usage Table */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  LLM Usage & Costs
                </Typography>
                {llmUsage && llmUsage.length > 0 ? (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Provider</TableCell>
                          <TableCell>Model</TableCell>
                          <TableCell align="right">Requests</TableCell>
                          <TableCell align="right">Tokens</TableCell>
                          <TableCell align="right">Cost (USD)</TableCell>
                          <TableCell align="right">Avg Latency (ms)</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {llmUsage.map((row) => (
                          <TableRow key={`${row.provider}-${row.model}`}>
                            <TableCell>
                              {row.provider.charAt(0).toUpperCase() + row.provider.slice(1)}
                            </TableCell>
                            <TableCell>{row.model}</TableCell>
                            <TableCell align="right">
                              {row.total_requests.toLocaleString()}
                            </TableCell>
                            <TableCell align="right">
                              {row.total_tokens.toLocaleString()}
                            </TableCell>
                            <TableCell align="right">${row.total_cost_usd.toFixed(4)}</TableCell>
                            <TableCell align="right">{row.avg_latency_ms.toFixed(0)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <Typography color="text.secondary">
                      No LLM usage data yet. Usage will appear after generating resumes or
                      analyzing jobs.
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

export default AnalyticsPage;
