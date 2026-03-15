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
import type { Education } from '@/types/settings';

interface EducationFormProps {
  entries: Education[];
  onChange: (entries: Education[]) => void;
}

const EMPTY_ENTRY: Education = {
  degree: '',
  institution: '',
  graduation_year: '',
  gpa: '',
};

function EducationForm({ entries, onChange }: EducationFormProps) {
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
    (index: number, field: keyof Education, value: string) => {
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
              Education {index + 1}
            </Typography>
            <IconButton
              size="small"
              color="error"
              onClick={() => removeEntry(index)}
              aria-label={`Remove education ${index + 1}`}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="Degree"
                placeholder="B.S. Computer Science"
                value={entry.degree}
                onChange={(e) => updateField(index, 'degree', e.target.value)}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                size="small"
                label="Institution"
                value={entry.institution}
                onChange={(e) => updateField(index, 'institution', e.target.value)}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                size="small"
                label="Graduation Year"
                placeholder="2023"
                value={entry.graduation_year}
                onChange={(e) => updateField(index, 'graduation_year', e.target.value)}
              />
            </Grid>
            <Grid item xs={6} sm={3}>
              <TextField
                fullWidth
                size="small"
                label="GPA (optional)"
                placeholder="3.8"
                value={entry.gpa ?? ''}
                onChange={(e) => updateField(index, 'gpa', e.target.value)}
              />
            </Grid>
          </Grid>
        </Box>
      ))}
      <Button variant="outlined" startIcon={<AddIcon />} onClick={addEntry} size="small">
        Add Education
      </Button>
    </Box>
  );
}

export default EducationForm;
