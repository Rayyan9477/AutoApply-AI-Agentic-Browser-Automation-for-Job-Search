import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import LinearProgress from '@mui/material/LinearProgress';
import Chip from '@mui/material/Chip';

import type { ResumeScoreResponse } from '@/types/resume';

interface ATSScoreCardProps {
  score: ResumeScoreResponse;
}

interface ScoreBarProps {
  label: string;
  value: number;
}

function ScoreBar({ label, value }: ScoreBarProps) {
  const percent = Math.round(value * 100);
  const color =
    percent >= 75 ? 'success' : percent >= 50 ? 'warning' : ('error' as const);

  return (
    <Box sx={{ mb: 1.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
        <Typography variant="body2">{label}</Typography>
        <Typography variant="body2" fontWeight={600}>
          {percent}%
        </Typography>
      </Box>
      <LinearProgress variant="determinate" value={percent} color={color} />
    </Box>
  );
}

function ATSScoreCard({ score }: ATSScoreCardProps) {
  const overallPercent = Math.round(score.overall_score * 100);

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          ATS Score Breakdown
        </Typography>

        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 3,
          }}
        >
          <Box
            sx={{
              width: 100,
              height: 100,
              borderRadius: '50%',
              border: '4px solid',
              borderColor:
                overallPercent >= 75
                  ? 'success.main'
                  : overallPercent >= 50
                    ? 'warning.main'
                    : 'error.main',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Typography variant="h4" fontWeight={700}>
              {overallPercent}
            </Typography>
          </Box>
        </Box>

        <ScoreBar label="Skills" value={score.skill_score} />
        <ScoreBar label="Experience" value={score.experience_score} />
        <ScoreBar label="Education" value={score.education_score} />
        <ScoreBar label="Keywords" value={score.keyword_score} />

        {score.missing_skills.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Missing Skills
            </Typography>
            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
              {score.missing_skills.map((skill) => (
                <Chip key={skill} label={skill} size="small" color="error" variant="outlined" />
              ))}
            </Box>
          </Box>
        )}

        {score.suggestions.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Suggestions
            </Typography>
            {score.suggestions.map((suggestion, index) => (
              <Typography key={index} variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                - {suggestion}
              </Typography>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

export default ATSScoreCard;
