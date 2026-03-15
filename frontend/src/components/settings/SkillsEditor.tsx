import { useState, useCallback } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import AddIcon from '@mui/icons-material/Add';

interface SkillsEditorProps {
  skills: string[];
  onChange: (skills: string[]) => void;
  label?: string;
}

function SkillsEditor({ skills, onChange, label = 'Add skill' }: SkillsEditorProps) {
  const [input, setInput] = useState('');

  const addSkill = useCallback(() => {
    const trimmed = input.trim();
    if (trimmed && !skills.includes(trimmed)) {
      onChange([...skills, trimmed]);
      setInput('');
    }
  }, [input, skills, onChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addSkill();
      }
    },
    [addSkill],
  );

  const handleDelete = useCallback(
    (index: number) => {
      onChange(skills.filter((_, i) => i !== index));
    },
    [skills, onChange],
  );

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <TextField
          size="small"
          label={label}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          fullWidth
        />
        <Button
          variant="outlined"
          onClick={addSkill}
          disabled={!input.trim()}
          startIcon={<AddIcon />}
          sx={{ whiteSpace: 'nowrap' }}
        >
          Add
        </Button>
      </Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
        {skills.map((skill, index) => (
          <Chip
            key={`${skill}-${index}`}
            label={skill}
            onDelete={() => handleDelete(index)}
            color="primary"
            variant="outlined"
            size="small"
          />
        ))}
      </Box>
    </Box>
  );
}

export default SkillsEditor;
