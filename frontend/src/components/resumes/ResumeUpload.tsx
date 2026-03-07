import { useCallback, useState, useRef } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import LinearProgress from '@mui/material/LinearProgress';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';

import { useUploadResume } from '@/hooks/useResumes';
import { useAppStore } from '@/store/useAppStore';

function ResumeUpload() {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMutation = useUploadResume();
  const showNotification = useAppStore((s) => s.showNotification);

  const handleFile = useCallback(
    (file: File) => {
      const validTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      ];
      if (!validTypes.includes(file.type)) {
        showNotification('Please upload a PDF or DOCX file.', 'error');
        return;
      }
      uploadMutation.mutate(file, {
        onSuccess: (data) => {
          showNotification(
            `Resume "${data.name}" uploaded. Detected ${data.skills_detected.length} skills.`,
            'success',
          );
        },
        onError: () => {
          showNotification('Failed to upload resume. Please try again.', 'error');
        },
      });
    },
    [uploadMutation, showNotification],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <Box
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      sx={{
        border: '2px dashed',
        borderColor: dragOver ? 'primary.main' : 'divider',
        borderRadius: 2,
        p: 4,
        textAlign: 'center',
        bgcolor: dragOver ? 'action.hover' : 'background.paper',
        cursor: 'pointer',
        transition: 'all 0.2s ease-in-out',
      }}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx"
        hidden
        onChange={handleInputChange}
      />

      {uploadMutation.isPending ? (
        <Box>
          <Typography variant="body1" gutterBottom>
            Uploading resume...
          </Typography>
          <LinearProgress sx={{ maxWidth: 300, mx: 'auto' }} />
        </Box>
      ) : (
        <>
          <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
          <Typography variant="h6" gutterBottom>
            Drop your resume here
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Supports PDF and DOCX files
          </Typography>
          <Button variant="outlined" startIcon={<InsertDriveFileIcon />}>
            Browse Files
          </Button>
        </>
      )}
    </Box>
  );
}

export default ResumeUpload;
