import { useState, useCallback } from 'react';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Pagination from '@mui/material/Pagination';
import Alert from '@mui/material/Alert';
import InboxIcon from '@mui/icons-material/Inbox';

import ApplicationCard from '@/components/applications/ApplicationCard';
import LoadingState from '@/components/common/LoadingState';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { useApplications, useApproveApplication } from '@/hooks/useApplications';
import { useAppStore } from '@/store/useAppStore';

const STATUS_TABS = [
  { label: 'All', value: undefined },
  { label: 'Pending', value: 'pending' },
  { label: 'Approved', value: 'approved' },
  { label: 'Applied', value: 'applied' },
  { label: 'Interview', value: 'interview' },
  { label: 'Offer', value: 'offer' },
  { label: 'Rejected', value: 'rejected' },
];

function ApplicationsPage() {
  const [tabIndex, setTabIndex] = useState(0);
  const [page, setPage] = useState(1);
  const showNotification = useAppStore((s) => s.showNotification);

  const currentStatus = STATUS_TABS[tabIndex]?.value;
  const { data: appsData, isLoading, isError } = useApplications(page, 20, currentStatus);
  const approveMutation = useApproveApplication();

  const handleTabChange = useCallback((_: React.SyntheticEvent, newValue: number) => {
    setTabIndex(newValue);
    setPage(1);
  }, []);

  const handleApprove = useCallback(
    (appId: string) => {
      approveMutation.mutate(appId, {
        onSuccess: () => showNotification('Application approved for auto-apply.', 'success'),
        onError: () => showNotification('Failed to approve application.', 'error'),
      });
    },
    [approveMutation, showNotification],
  );

  const handlePageChange = useCallback((_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  }, []);

  return (
    <ErrorBoundary>
      <Box>
        <Typography variant="h4" gutterBottom>
          Applications
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Track and manage your job applications
        </Typography>

        <Tabs
          value={tabIndex}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}
        >
          {STATUS_TABS.map((tab) => (
            <Tab key={tab.label} label={tab.label} />
          ))}
        </Tabs>

        {isLoading && <LoadingState message="Loading applications..." />}

        {isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to load applications. Please try again.
          </Alert>
        )}

        {!isLoading && !isError && appsData && appsData.items.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <InboxIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">
              No applications found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {currentStatus
                ? `No applications with status "${currentStatus}".`
                : 'Apply to jobs from the Job Search page to get started.'}
            </Typography>
          </Box>
        )}

        {appsData && appsData.items.length > 0 && (
          <>
            <Grid container spacing={2}>
              {appsData.items.map((app) => (
                <Grid item xs={12} sm={6} lg={4} key={app.id}>
                  <ApplicationCard application={app} onApprove={handleApprove} />
                </Grid>
              ))}
            </Grid>

            {appsData.total > 20 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                <Pagination
                  count={Math.ceil(appsData.total / 20)}
                  page={page}
                  onChange={handlePageChange}
                  color="primary"
                />
              </Box>
            )}
          </>
        )}
      </Box>
    </ErrorBoundary>
  );
}

export default ApplicationsPage;
