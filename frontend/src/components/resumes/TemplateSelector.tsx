import { useState } from 'react';
import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActionArea from '@mui/material/CardActionArea';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DescriptionIcon from '@mui/icons-material/Description';

interface Template {
  id: string;
  name: string;
  description: string;
}

const TEMPLATES: Template[] = [
  { id: 'modern', name: 'Modern', description: 'Clean layout with sidebar accent' },
  { id: 'classic', name: 'Classic', description: 'Traditional professional format' },
  { id: 'minimal', name: 'Minimal', description: 'Simple and elegant design' },
  { id: 'technical', name: 'Technical', description: 'Optimized for engineering roles' },
  { id: 'creative', name: 'Creative', description: 'Eye-catching visual layout' },
];

interface TemplateSelectorProps {
  selectedId?: string;
  onSelect: (templateId: string) => void;
}

function TemplateSelector({ selectedId, onSelect }: TemplateSelectorProps) {
  const [selected, setSelected] = useState(selectedId ?? 'modern');

  const handleSelect = (id: string) => {
    setSelected(id);
    onSelect(id);
  };

  return (
    <Grid container spacing={2}>
      {TEMPLATES.map((template) => {
        const isSelected = selected === template.id;
        return (
          <Grid item xs={12} sm={6} md={4} lg={2.4} key={template.id}>
            <Card
              sx={{
                borderColor: isSelected ? 'primary.main' : 'divider',
                borderWidth: isSelected ? 2 : 1,
                position: 'relative',
              }}
            >
              <CardActionArea onClick={() => handleSelect(template.id)}>
                <CardContent sx={{ textAlign: 'center', py: 3 }}>
                  {isSelected && (
                    <CheckCircleIcon
                      color="primary"
                      sx={{ position: 'absolute', top: 8, right: 8 }}
                    />
                  )}
                  <Box
                    sx={{
                      width: 60,
                      height: 80,
                      mx: 'auto',
                      mb: 1.5,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      bgcolor: isSelected ? 'primary.light' : 'grey.100',
                      borderRadius: 1,
                      transition: 'background-color 0.2s',
                    }}
                  >
                    <DescriptionIcon
                      sx={{ fontSize: 32, color: isSelected ? 'white' : 'grey.500' }}
                    />
                  </Box>
                  <Typography variant="subtitle2" fontWeight={600}>
                    {template.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {template.description}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        );
      })}
    </Grid>
  );
}

export default TemplateSelector;
