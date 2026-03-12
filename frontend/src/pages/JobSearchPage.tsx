import { useCallback, useState } from 'react';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Pagination from '@mui/material/Pagination';
import Alert from '@mui/material/Alert';
import SearchIcon from '@mui/icons-material/Search';

import JobFilters from '@/components/jobs/JobFilters';
import JobCard from '@/components/jobs/JobCard';
import JobDetail from '@/components/jobs/JobDetail';
import LoadingState from '@/components/common/LoadingState';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { useJobs, useSearchJobs } from '@/hooks/useJobs';
import { useCreateApplication } from '@/hooks/useApplications';
import { useJobStore } from '@/store/useJobStore';
import { useAppStore } from '@/store/useAppStore';

function JobSearchPage() {
  const [page, setPage] = useState(1);
  const searchQuery = useJobStore((s) => s.searchQuery);
  const locationFilter = useJobStore((s) => s.locationFilter);
  const platformFilters = useJobStore((s) => s.platformFilters);
  const selectedJobId = useJobStore((s) => s.selectedJobId);
  const detailOpen = useJobStore((s) => s.detailOpen);
  const openDetail = useJobStore((s) => s.openDetail);
  const closeDetail = useJobStore((s) => s.closeDetail);
  const showNotification = useAppStore((s) => s.showNotification);

  const { data: jobsData, isLoading, isError } = useJobs(page, 20);
  const searchMutation = useSearchJobs();
  const createAppMutation = useCreateApplication();

  const handleApply = useCallback(
    (jobId: string) => {
      createAppMutation.mutate(
        { job_id: jobId },
        {
          onSuccess: () => showNotification('Application created successfully.', 'success'),
          onError: () => showNotification('Failed to create application.', 'error'),
        },
      );
    },
    [createAppMutation, showNotification],
  );

  const handleSearch = useCallback(() => {
    if (!searchQuery.trim()) return;
    searchMutation.mutate(
      {
        query: searchQuery,
        location: locationFilter || undefined,
        platforms: platformFilters,
        limit: 20,
      },
      {
        onSuccess: (result) => {
          showNotification(`Found ${result.total} jobs across ${platformFilters.length} platforms.`, 'success');
        },
        onError: () => {
          showNotification('Job search failed. Please try again.', 'error');
        },
      },
    );
  }, [searchQuery, locationFilter, platformFilters, searchMutation, showNotification]);

  const handlePageChange = useCallback((_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  }, []);

  return (
    <ErrorBoundary>
      <Box>
        <Typography variant="h4" gutterBottom>
          Job Search
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Search across LinkedIn, Indeed, and Glassdoor
        </Typography>

        <JobFilters onSearch={handleSearch} loading={searchMutation.isPending} />

        {isLoading && <LoadingState message="Loading jobs..." />}

        {isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to load jobs. Please check your connection and try again.
          </Alert>
        )}

        {!isLoading && !isError && jobsData && jobsData.items.length === 0 && (
          <Box
            sx={{
              textAlign: 'center',
              py: 8,
            }}
          >
            <SearchIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">
              No jobs found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Try searching for a job title or keyword above.
            </Typography>
          </Box>
        )}

        {jobsData && jobsData.items.length > 0 && (
          <>
            <Grid container spacing={2}>
              {jobsData.items.map((job) => (
                <Grid item xs={12} sm={6} lg={4} key={job.id}>
                  <JobCard
                    job={job}
                    onViewDetails={openDetail}
                    onApply={handleApply}
                  />
                </Grid>
              ))}
            </Grid>

            {jobsData.total > 20 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                <Pagination
                  count={Math.ceil(jobsData.total / 20)}
                  page={page}
                  onChange={handlePageChange}
                  color="primary"
                />
              </Box>
            )}
          </>
        )}

        <JobDetail
          jobId={selectedJobId}
          open={detailOpen}
          onClose={closeDetail}
          onApply={handleApply}
        />
      </Box>
    </ErrorBoundary>
  );
}

export default JobSearchPage;
