import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import type { LLMProviderStatus } from '@/types/settings';

interface LLMProvidersCardProps {
  providers: LLMProviderStatus[] | undefined;
}

function LLMProvidersCard({ providers }: LLMProvidersCardProps) {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          LLM Providers
        </Typography>

        <Divider sx={{ mb: 2 }} />

        <Grid container spacing={2}>
          {providers?.map((provider) => (
            <Grid item xs={12} sm={4} key={provider.provider}>
              <Box
                sx={{
                  p: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 1,
                  }}
                >
                  <Typography variant="subtitle1" fontWeight={600}>
                    {provider.provider.charAt(0).toUpperCase() + provider.provider.slice(1)}
                  </Typography>
                  {provider.configured ? (
                    <CheckCircleIcon color="success" fontSize="small" />
                  ) : (
                    <CancelIcon color="disabled" fontSize="small" />
                  )}
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Model: {provider.model}
                </Typography>
                <Box sx={{ mt: 1 }}>
                  <Chip
                    label={provider.configured ? 'Configured' : 'Not Configured'}
                    size="small"
                    color={provider.configured ? 'success' : 'default'}
                    variant="outlined"
                  />
                  {provider.is_primary && (
                    <Chip
                      label="Primary"
                      size="small"
                      color="primary"
                      sx={{ ml: 0.5 }}
                    />
                  )}
                </Box>
              </Box>
            </Grid>
          )) ?? (
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary">
                Loading provider information...
              </Typography>
            </Grid>
          )}
        </Grid>
      </CardContent>
    </Card>
  );
}

export default LLMProvidersCard;
