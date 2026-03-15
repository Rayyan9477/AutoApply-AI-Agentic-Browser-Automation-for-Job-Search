import { useCallback } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import Grid from '@mui/material/Grid';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import type { WorkExperience } from '@/types/settings';

interface ExperienceFormProps {
  entries: WorkExperience[];
  onChange: (entries: WorkExperience[]) => void;
}

const EMPTY_ENTRY: WorkExperience = {
  title: '',
  company: '',
  start_date: '',
  end_date: '',
  description: '',
  responsibilities: [],
};

function ExperienceForm({ entries, onChange }: ExperienceFormProps) {
  const addEntry = useCallback(() => {
    onChange([...entries, { ...EMPTY_ENTRY }]);
  }, [entries, onChange]);

  const removeEntry = useCallback(
    (index: number) => {
      onChange(entries.filter((_, i) => i !== index));
    },
    [entries, onChange],
  );

  const updateField = useCallback(
    (index: number, field: keyof WorkExperience, value: string) => {
      const updated = entries.map((entry, i) =>
        i === index ? { ...entry, [field]: value } : entry,
      );
      onChange(updated);
    },
    [entries, onChange],
  );

  return (
    <Box>
      {entries.map((entry, index) => (
        <Box key={index} sx={{ mb: 3 }}>
          {index > 0 && <Divider sx={{ mb: 2 }} />}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Position {index + 1}
            </Typography>
            <IconButton
              size="small"
              color="error"
              onClick={() => removeEntry(index)}
              aria-label={`Remove position ${index + 1}`}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="Job Title"
                value={entry.title}
                onChange={(e) => updateField(index, 'title', e.target.value)}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="Company"
                value={entry.company}
                onChange={(e) => updateField(index, 'company', e.target.value)}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                size="small"
                label="Start Date"
                placeholder="Jan 2020"
                value={entry.start_date}
                onChange={(e) => updateField(index, 'start_date', e.target.value)}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                size="small"
                label="End Date"
                placeholder="Present"
                value={entry.end_date}
                onChange={(e) => updateField(index, 'end_date', e.target.value)}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Description"
                multiline
                minRows={2}
                maxRows={5}
                value={entry.description}
                onChange={(e) => updateField(index, 'description', e.target.value)}
              />
            </Grid>
          </Grid>
        </Box>
      ))}
      <Button variant="outlined" startIcon={<AddIcon />} onClick={addEntry} size="small">
        Add Position
      </Button>
    </Box>
  );
}

export default ExperienceForm;
