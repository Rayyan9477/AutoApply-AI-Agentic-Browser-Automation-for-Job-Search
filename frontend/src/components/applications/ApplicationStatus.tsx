import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Box from '@mui/material/Box';

const STEPS = ['Pending', 'Approved', 'Applied', 'Interview', 'Offer'];

const STATUS_TO_STEP: Record<string, number> = {
  pending: 0,
  approved: 1,
  applied: 2,
  interview: 3,
  offer: 4,
  rejected: -1,
};

interface ApplicationStatusProps {
  status: string;
}

function ApplicationStatusStepper({ status }: ApplicationStatusProps) {
  const activeStep = STATUS_TO_STEP[status] ?? 0;
  const isRejected = status === 'rejected';

  return (
    <Box sx={{ width: '100%', py: 2 }}>
      <Stepper activeStep={isRejected ? -1 : activeStep} alternativeLabel>
        {STEPS.map((label) => (
          <Step key={label}>
            <StepLabel
              error={isRejected}
              sx={isRejected ? { '& .MuiStepLabel-label': { color: 'error.main' } } : undefined}
            >
              {isRejected && label === 'Pending' ? 'Rejected' : label}
            </StepLabel>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
}

export default ApplicationStatusStepper;
