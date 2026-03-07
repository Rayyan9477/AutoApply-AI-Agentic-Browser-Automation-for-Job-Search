import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import BusinessIcon from '@mui/icons-material/Business';
import StarIcon from '@mui/icons-material/Star';

import type { Job } from '@/types/job';

interface JobCardProps {
  job: Job;
  onViewDetails: (jobId: string) => void;
  onApply?: (jobId: string) => void;
}

function JobCard({ job, onViewDetails, onApply }: JobCardProps) {
  const matchPercent = job.match_score != null ? Math.round(job.match_score * 100) : null;

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="h6" noWrap gutterBottom>
              {job.title}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
              <BusinessIcon fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {job.company}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
              <LocationOnIcon fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {job.location || 'Remote'}
              </Typography>
            </Box>
          </Box>

          {matchPercent !== null && (
            <Chip
              icon={<StarIcon />}
              label={`${matchPercent}%`}
              color={matchPercent >= 75 ? 'success' : matchPercent >= 50 ? 'warning' : 'default'}
              size="small"
              sx={{ fontWeight: 600 }}
            />
          )}
        </Box>

        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
          <Chip label={job.platform} size="small" variant="outlined" />
          {job.remote && <Chip label="Remote" size="small" color="info" variant="outlined" />}
          {job.job_type && <Chip label={job.job_type} size="small" variant="outlined" />}
          {job.salary_range && (
            <Chip label={job.salary_range} size="small" color="secondary" variant="outlined" />
          )}
        </Box>
      </CardContent>

      <CardActions sx={{ px: 2, pb: 2 }}>
        <Button size="small" onClick={() => onViewDetails(job.id)}>
          View Details
        </Button>
        {onApply && (
          <Button size="small" variant="contained" onClick={() => onApply(job.id)}>
            Apply
          </Button>
        )}
      </CardActions>
    </Card>
  );
}

export default JobCard;
