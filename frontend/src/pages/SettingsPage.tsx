import { useCallback } from 'react';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import type { SelectChangeEvent } from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Slider from '@mui/material/Slider';
import FormGroup from '@mui/material/FormGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';

import LoadingState from '@/components/common/LoadingState';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { useSettings, useUpdateSettings, useLLMProviders } from '@/hooks/useSettings';
import { useAppStore } from '@/store/useAppStore';

const PLATFORMS = ['linkedin', 'indeed', 'glassdoor'];

function SettingsPage() {
  const { data: settings, isLoading } = useSettings();
  const { data: llmProviders } = useLLMProviders();
  const updateMutation = useUpdateSettings();
  const showNotification = useAppStore((s) => s.showNotification);

  const handleUpdate = useCallback(
    (field: string, value: unknown) => {
      updateMutation.mutate(
        { [field]: value },
        {
          onSuccess: () => showNotification('Settings saved.', 'success'),
          onError: () => showNotification('Failed to save settings.', 'error'),
        },
      );
    },
    [updateMutation, showNotification],
  );

  const handleApplyModeChange = useCallback(
    (event: SelectChangeEvent) => {
      handleUpdate('apply_mode', event.target.value);
    },
    [handleUpdate],
  );

  const handleATSThresholdChange = useCallback(
    (_: Event, value: number | number[]) => {
      if (typeof value === 'number') {
        handleUpdate('min_ats_score', value / 100);
      }
    },
    [handleUpdate],
  );

  const handleParallelChange = useCallback(
    (_: Event, value: number | number[]) => {
      if (typeof value === 'number') {
        handleUpdate('max_parallel', value);
      }
    },
    [handleUpdate],
  );

  const handlePlatformToggle = useCallback(
    (platform: string, enabled: boolean) => {
      if (!settings) return;
      const updated = enabled
        ? [...settings.platforms_enabled, platform]
        : settings.platforms_enabled.filter((p) => p !== platform);
      handleUpdate('platforms_enabled', updated);
    },
    [settings, handleUpdate],
  );

  if (isLoading) {
    return <LoadingState message="Loading settings..." />;
  }

  return (
    <ErrorBoundary>
      <Box>
        <Typography variant="h4" gutterBottom>
          Settings
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Configure your AutoApply preferences
        </Typography>

        <Grid container spacing={3}>
          {/* Apply Mode */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Application Mode
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Control how applications are submitted.
                </Typography>

                <FormControl fullWidth>
                  <InputLabel>Apply Mode</InputLabel>
                  <Select
                    value={settings?.apply_mode ?? 'review'}
                    onChange={handleApplyModeChange}
                    label="Apply Mode"
                  >
                    <MenuItem value="autonomous">Autonomous (fully automated)</MenuItem>
                    <MenuItem value="review">Review per Job (approve each)</MenuItem>
                    <MenuItem value="batch">Batch Review (approve in bulk)</MenuItem>
                  </Select>
                </FormControl>
              </CardContent>
            </Card>
          </Grid>

          {/* ATS Threshold */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  ATS Score Threshold
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Minimum ATS score required before auto-applying.
                </Typography>

                <Box sx={{ px: 1 }}>
                  <Slider
                    value={Math.round((settings?.min_ats_score ?? 0.75) * 100)}
                    onChange={handleATSThresholdChange}
                    min={0}
                    max={100}
                    step={5}
                    marks={[
                      { value: 0, label: '0%' },
                      { value: 50, label: '50%' },
                      { value: 100, label: '100%' },
                    ]}
                    valueLabelDisplay="on"
                    valueLabelFormat={(v) => `${v}%`}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Parallel Sessions */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Parallel Browser Sessions
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Number of simultaneous browser sessions for auto-apply.
                </Typography>

                <Box sx={{ px: 1 }}>
                  <Slider
                    value={settings?.max_parallel ?? 3}
                    onChange={handleParallelChange}
                    min={1}
                    max={5}
                    step={1}
                    marks={[
                      { value: 1, label: '1' },
                      { value: 3, label: '3' },
                      { value: 5, label: '5' },
                    ]}
                    valueLabelDisplay="auto"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Platform Toggles */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Job Platforms
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Enable or disable job search platforms.
                </Typography>

                <FormGroup>
                  {PLATFORMS.map((platform) => (
                    <FormControlLabel
                      key={platform}
                      control={
                        <Switch
                          checked={settings?.platforms_enabled.includes(platform) ?? false}
                          onChange={(e) => handlePlatformToggle(platform, e.target.checked)}
                        />
                      }
                      label={platform.charAt(0).toUpperCase() + platform.slice(1)}
                    />
                  ))}
                </FormGroup>
              </CardContent>
            </Card>
          </Grid>

          {/* LLM Providers */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  LLM Providers
                </Typography>

                <Divider sx={{ mb: 2 }} />

                <Grid container spacing={2}>
                  {llmProviders?.map((provider) => (
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
          </Grid>
        </Grid>
      </Box>
    </ErrorBoundary>
  );
}

export default SettingsPage;
