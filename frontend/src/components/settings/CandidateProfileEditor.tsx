import { useState, useCallback, useEffect } from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PersonIcon from '@mui/icons-material/Person';
import WorkIcon from '@mui/icons-material/Work';
import SchoolIcon from '@mui/icons-material/School';
import CodeIcon from '@mui/icons-material/Code';
import DescriptionIcon from '@mui/icons-material/Description';
import VerifiedIcon from '@mui/icons-material/Verified';
import SaveIcon from '@mui/icons-material/Save';
import type { CandidateProfile } from '@/types/settings';
import SkillsEditor from './SkillsEditor';
import ExperienceForm from './ExperienceForm';
import EducationForm from './EducationForm';

interface CandidateProfileEditorProps {
  profile: CandidateProfile | null;
  onSave: (profile: CandidateProfile) => void;
}

const EMPTY_PROFILE: CandidateProfile = {
  full_name: '',
  email: '',
  phone: '',
  location: '',
  linkedin_url: '',
  github_url: '',
  summary: '',
  skills: [],
  experience: [],
  education: [],
  certifications: [],
};

function CandidateProfileEditor({ profile, onSave }: CandidateProfileEditorProps) {
  const [form, setForm] = useState<CandidateProfile>({ ...EMPTY_PROFILE });

  useEffect(() => {
    if (profile) {
      setForm({
        ...EMPTY_PROFILE,
        ...profile,
      });
    }
  }, [profile]);

  const updateField = useCallback(
    <K extends keyof CandidateProfile>(field: K, value: CandidateProfile[K]) => {
      setForm((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const handleTextChange = useCallback(
    (field: keyof CandidateProfile) =>
      (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        updateField(field, e.target.value as CandidateProfile[typeof field]);
      },
    [updateField],
  );

  const handleSave = useCallback(() => {
    onSave(form);
  }, [form, onSave]);

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Candidate Profile
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Your profile information is used to generate tailored resumes and cover letters.
        </Typography>

        {/* Personal Info */}
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <PersonIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography fontWeight={600}>Personal Information</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth size="small" label="Full Name"
                  value={form.full_name} onChange={handleTextChange('full_name')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth size="small" label="Email"
                  value={form.email} onChange={handleTextChange('email')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth size="small" label="Phone"
                  value={form.phone} onChange={handleTextChange('phone')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth size="small" label="Location"
                  placeholder="San Francisco, CA"
                  value={form.location} onChange={handleTextChange('location')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth size="small" label="LinkedIn URL"
                  value={form.linkedin_url} onChange={handleTextChange('linkedin_url')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth size="small" label="GitHub URL"
                  value={form.github_url} onChange={handleTextChange('github_url')}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Professional Summary */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <DescriptionIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography fontWeight={600}>Professional Summary</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TextField
              fullWidth multiline minRows={3} maxRows={8} size="small"
              label="Summary"
              placeholder="Experienced software engineer with 5+ years..."
              value={form.summary} onChange={handleTextChange('summary')}
            />
          </AccordionDetails>
        </Accordion>

        {/* Skills */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <CodeIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography fontWeight={600}>Skills</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <SkillsEditor
              skills={form.skills}
              onChange={(skills) => updateField('skills', skills)}
            />
          </AccordionDetails>
        </Accordion>

        {/* Work Experience */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <WorkIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography fontWeight={600}>Work Experience</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <ExperienceForm
              entries={form.experience}
              onChange={(experience) => updateField('experience', experience)}
            />
          </AccordionDetails>
        </Accordion>

        {/* Education */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <SchoolIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography fontWeight={600}>Education</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <EducationForm
              entries={form.education}
              onChange={(education) => updateField('education', education)}
            />
          </AccordionDetails>
        </Accordion>

        {/* Certifications */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <VerifiedIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography fontWeight={600}>Certifications</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <SkillsEditor
              skills={form.certifications}
              onChange={(certifications) => updateField('certifications', certifications)}
              label="Add certification"
            />
          </AccordionDetails>
        </Accordion>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            size="large"
          >
            Save Profile
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}

export default CandidateProfileEditor;
