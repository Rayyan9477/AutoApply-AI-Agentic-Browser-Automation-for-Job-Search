import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import CancelIcon from '@mui/icons-material/Cancel';
import SendIcon from '@mui/icons-material/Send';
import EmojiEventsIcon from '@mui/icons-material/EmojiEvents';

import type { Application } from '@/types/application';

interface ApplicationCardProps {
  application: Application;
  onApprove?: (appId: string) => void;
  onUpdateStatus?: (appId: string) => void;
}

const STATUS_CONFIG: Record<
  string,
  { color: 'default' | 'warning' | 'info' | 'success' | 'error'; icon: React.ReactElement }
> = {
  pending: { color: 'warning', icon: <HourglassEmptyIcon fontSize="small" /> },
  approved: { color: 'info', icon: <CheckCircleIcon fontSize="small" /> },
  applied: { color: 'success', icon: <SendIcon fontSize="small" /> },
  interview: { color: 'success', icon: <EmojiEventsIcon fontSize="small" /> },
  rejected: { color: 'error', icon: <CancelIcon fontSize="small" /> },
  offer: { color: 'success', icon: <EmojiEventsIcon fontSize="small" /> },
};

function ApplicationCard({ application, onApprove, onUpdateStatus }: ApplicationCardProps) {
  const statusConf = STATUS_CONFIG[application.status] ?? {
    color: 'default' as const,
    icon: <HourglassEmptyIcon fontSize="small" />,
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="subtitle1" fontWeight={600} noWrap>
              Application #{application.id.slice(0, 8)}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
              Job: {application.job_id.slice(0, 8)}...
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Mode: {application.apply_mode}
            </Typography>
          </Box>

          <Chip
            icon={statusConf.icon}
            label={application.status.charAt(0).toUpperCase() + application.status.slice(1)}
            color={statusConf.color}
            size="small"
          />
        </Box>

        {application.ats_score != null && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              ATS Score: {Math.round(application.ats_score * 100)}%
            </Typography>
          </Box>
        )}

        {application.notes && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {application.notes}
          </Typography>
        )}

        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          Created: {new Date(application.created_at).toLocaleDateString()}
          {application.applied_at &&
            ` | Applied: ${new Date(application.applied_at).toLocaleDateString()}`}
        </Typography>
      </CardContent>

      <CardActions sx={{ px: 2, pb: 2 }}>
        {application.status === 'pending' && onApprove && (
          <Button size="small" variant="contained" onClick={() => onApprove(application.id)}>
            Approve
          </Button>
        )}
        {onUpdateStatus && (
          <Button size="small" onClick={() => onUpdateStatus(application.id)}>
            Update Status
          </Button>
        )}
      </CardActions>
    </Card>
  );
}

export default ApplicationCard;
