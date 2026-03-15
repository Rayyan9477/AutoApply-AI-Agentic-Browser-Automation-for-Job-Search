import { useState, useCallback } from 'react';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActions from '@mui/material/CardActions';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import DescriptionIcon from '@mui/icons-material/Description';
import DownloadIcon from '@mui/icons-material/Download';

import ResumeUpload from '@/components/resumes/ResumeUpload';
import TemplateSelector from '@/components/resumes/TemplateSelector';
import LoadingState from '@/components/common/LoadingState';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import { useResumes } from '@/hooks/useResumes';
import { getDownloadUrl } from '@/services/resumeService';

function ResumesPage() {
  const [selectedTemplate, setSelectedTemplate] = useState('modern');
  const { data: resumeData, isLoading } = useResumes();

  const handleTemplateSelect = useCallback((templateId: string) => {
    setSelectedTemplate(templateId);
  }, []);

  return (
    <ErrorBoundary>
      <Box>
        <Typography variant="h4" gutterBottom>
          Resumes
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Upload, generate, and manage your resumes
        </Typography>

        <ResumeUpload />

        <Box sx={{ mt: 4, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Resume Templates
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Select a template for generating tailored resumes. Currently selected:{' '}
            <strong>{selectedTemplate}</strong>
          </Typography>
          <TemplateSelector selectedId={selectedTemplate} onSelect={handleTemplateSelect} />
        </Box>

        <Divider sx={{ my: 4 }} />

        <Typography variant="h6" gutterBottom>
          Your Resumes
        </Typography>

        {isLoading && <LoadingState message="Loading resumes..." minHeight={200} />}

        {!isLoading && resumeData && resumeData.items.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <DescriptionIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">
              No resumes yet
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Upload your first resume to get started with ATS optimization.
            </Typography>
          </Box>
        )}

        {resumeData && resumeData.items.length > 0 && (
          <Grid container spacing={2}>
            {resumeData.items.map((resume) => (
              <Grid item xs={12} sm={6} md={4} key={resume.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <DescriptionIcon color="primary" />
                      <Typography variant="subtitle1" fontWeight={600} noWrap>
                        {resume.name}
                      </Typography>
                    </Box>

                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1 }}>
                      <Chip label={resume.type} size="small" variant="outlined" />
                      <Chip label={resume.template_id} size="small" variant="outlined" />
                    </Box>

                    {resume.ats_score != null && (
                      <Typography variant="body2" color="text.secondary">
                        ATS Score: {Math.round(resume.ats_score * 100)}%
                      </Typography>
                    )}

                    <Typography variant="caption" color="text.secondary" display="block">
                      Created: {new Date(resume.created_at).toLocaleDateString()}
                    </Typography>
                  </CardContent>

                  <CardActions sx={{ px: 2, pb: 2 }}>
                    {resume.has_pdf && (
                      <Button
                        size="small"
                        startIcon={<DownloadIcon />}
                        href={getDownloadUrl(resume.id, 'pdf')}
                      >
                        PDF
                      </Button>
                    )}
                    {resume.has_docx && (
                      <Button
                        size="small"
                        startIcon={<DownloadIcon />}
                        href={getDownloadUrl(resume.id, 'docx')}
                      >
                        DOCX
                      </Button>
                    )}
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>
    </ErrorBoundary>
  );
}

export default ResumesPage;
