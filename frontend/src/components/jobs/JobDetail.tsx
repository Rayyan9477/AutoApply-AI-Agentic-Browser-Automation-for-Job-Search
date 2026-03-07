import Drawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import CloseIcon from '@mui/icons-material/Close';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import BusinessIcon from '@mui/icons-material/Business';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';

import { useJob } from '@/hooks/useJobs';
import LoadingState from '@/components/common/LoadingState';

interface JobDetailProps {
  jobId: string | null;
  open: boolean;
  onClose: () => void;
  onApply?: (jobId: string) => void;
}

function JobDetail({ jobId, open, onClose, onApply }: JobDetailProps) {
  const { data: job, isLoading, isError } = useJob(jobId ?? undefined);

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      sx={{
        '& .MuiDrawer-paper': { width: { xs: '100%', sm: 480 } },
      }}
    >
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Job Details</Typography>
          <IconButton onClick={onClose} aria-label="Close job details">
            <CloseIcon />
          </IconButton>
        </Box>

        {isLoading && <LoadingState message="Loading job details..." />}

        {isError && (
          <Typography color="error" variant="body2">
            Failed to load job details. Please try again.
          </Typography>
        )}

        {job && (
          <>
            <Typography variant="h5" gutterBottom>
              {job.title}
            </Typography>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
              <BusinessIcon fontSize="small" color="action" />
              <Typography variant="body1" color="text.secondary">
                {job.company}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
              <LocationOnIcon fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {job.location || 'Remote'}
              </Typography>
            </Box>

            {job.posted_date && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 2 }}>
                <CalendarTodayIcon fontSize="small" color="action" />
                <Typography variant="body2" color="text.secondary">
                  Posted {new Date(job.posted_date).toLocaleDateString()}
                </Typography>
              </Box>
            )}

            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 2 }}>
              <Chip label={job.platform} size="small" />
              {job.remote && <Chip label="Remote" size="small" color="info" />}
              {job.job_type && <Chip label={job.job_type} size="small" />}
              {job.experience_level && <Chip label={job.experience_level} size="small" />}
              {job.salary_range && <Chip label={job.salary_range} size="small" color="secondary" />}
            </Box>

            {job.match_score != null && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Match Score
                </Typography>
                <Chip
                  label={`${Math.round(job.match_score * 100)}%`}
                  color={
                    job.match_score >= 0.75
                      ? 'success'
                      : job.match_score >= 0.5
                        ? 'warning'
                        : 'default'
                  }
                />
              </Box>
            )}

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" gutterBottom>
              Description
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ whiteSpace: 'pre-wrap', mb: 3 }}
            >
              {job.description}
            </Typography>

            <Box sx={{ display: 'flex', gap: 1 }}>
              {onApply && (
                <Button variant="contained" onClick={() => onApply(job.id)}>
                  Apply Now
                </Button>
              )}
              <Button
                variant="outlined"
                endIcon={<OpenInNewIcon />}
                component={Link}
                href={job.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                View Original
              </Button>
            </Box>
          </>
        )}
      </Box>
    </Drawer>
  );
}

export default JobDetail;
