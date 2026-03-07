import { useCallback } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import type { SelectChangeEvent } from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Chip from '@mui/material/Chip';
import OutlinedInput from '@mui/material/OutlinedInput';
import Button from '@mui/material/Button';
import InputAdornment from '@mui/material/InputAdornment';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';

import { useJobStore } from '@/store/useJobStore';

const PLATFORM_OPTIONS = [
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'indeed', label: 'Indeed' },
  { value: 'glassdoor', label: 'Glassdoor' },
];

interface JobFiltersProps {
  onSearch: () => void;
  loading?: boolean;
}

function JobFilters({ onSearch, loading = false }: JobFiltersProps) {
  const searchQuery = useJobStore((s) => s.searchQuery);
  const setSearchQuery = useJobStore((s) => s.setSearchQuery);
  const locationFilter = useJobStore((s) => s.locationFilter);
  const setLocationFilter = useJobStore((s) => s.setLocationFilter);
  const platformFilters = useJobStore((s) => s.platformFilters);
  const setPlatformFilters = useJobStore((s) => s.setPlatformFilters);
  const resetFilters = useJobStore((s) => s.resetFilters);

  const handlePlatformChange = useCallback(
    (event: SelectChangeEvent<string[]>) => {
      const value = event.target.value;
      setPlatformFilters(typeof value === 'string' ? value.split(',') : value);
    },
    [setPlatformFilters],
  );

  const handleKeyPress = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === 'Enter') {
        onSearch();
      }
    },
    [onSearch],
  );

  return (
    <Box
      sx={{
        display: 'flex',
        gap: 2,
        flexWrap: 'wrap',
        alignItems: 'center',
        mb: 3,
      }}
    >
      <TextField
        placeholder="Search jobs (e.g. Software Engineer)"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        onKeyDown={handleKeyPress}
        size="small"
        sx={{ minWidth: 280, flex: 1 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon color="action" />
            </InputAdornment>
          ),
        }}
      />

      <TextField
        placeholder="Location"
        value={locationFilter}
        onChange={(e) => setLocationFilter(e.target.value)}
        onKeyDown={handleKeyPress}
        size="small"
        sx={{ minWidth: 180 }}
      />

      <FormControl size="small" sx={{ minWidth: 200 }}>
        <InputLabel>Platforms</InputLabel>
        <Select
          multiple
          value={platformFilters}
          onChange={handlePlatformChange}
          input={<OutlinedInput label="Platforms" />}
          renderValue={(selected) => (
            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
              {selected.map((value) => (
                <Chip key={value} label={value} size="small" />
              ))}
            </Box>
          )}
        >
          {PLATFORM_OPTIONS.map((opt) => (
            <MenuItem key={opt.value} value={opt.value}>
              {opt.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      <Button
        variant="contained"
        startIcon={<FilterListIcon />}
        onClick={onSearch}
        disabled={!searchQuery.trim() || loading}
      >
        Search
      </Button>

      <Button variant="text" size="small" onClick={resetFilters}>
        Reset
      </Button>
    </Box>
  );
}

export default JobFilters;
