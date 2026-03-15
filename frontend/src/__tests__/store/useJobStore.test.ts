import { describe, it, expect, beforeEach } from 'vitest';
import { useJobStore } from '@/store/useJobStore';

describe('useJobStore', () => {
  beforeEach(() => {
    // Reset to initial state before each test.
    useJobStore.setState({
      selectedJobId: null,
      searchQuery: '',
      locationFilter: '',
      platformFilters: ['linkedin', 'indeed', 'glassdoor'],
      detailOpen: false,
    });
  });

  it('has correct initial state', () => {
    const state = useJobStore.getState();
    expect(state.selectedJobId).toBeNull();
    expect(state.searchQuery).toBe('');
    expect(state.locationFilter).toBe('');
    expect(state.platformFilters).toEqual(['linkedin', 'indeed', 'glassdoor']);
    expect(state.detailOpen).toBe(false);
  });

  it('setSelectedJobId updates selectedJobId', () => {
    useJobStore.getState().setSelectedJobId('job-42');
    expect(useJobStore.getState().selectedJobId).toBe('job-42');
  });

  it('setSelectedJobId can clear selectedJobId with null', () => {
    useJobStore.getState().setSelectedJobId('job-42');
    useJobStore.getState().setSelectedJobId(null);
    expect(useJobStore.getState().selectedJobId).toBeNull();
  });

  it('setSearchQuery updates searchQuery', () => {
    useJobStore.getState().setSearchQuery('react developer');
    expect(useJobStore.getState().searchQuery).toBe('react developer');
  });

  it('setLocationFilter updates locationFilter', () => {
    useJobStore.getState().setLocationFilter('New York');
    expect(useJobStore.getState().locationFilter).toBe('New York');
  });

  it('setPlatformFilters updates platformFilters', () => {
    useJobStore.getState().setPlatformFilters(['linkedin']);
    expect(useJobStore.getState().platformFilters).toEqual(['linkedin']);
  });

  it('setPlatformFilters can set empty array', () => {
    useJobStore.getState().setPlatformFilters([]);
    expect(useJobStore.getState().platformFilters).toEqual([]);
  });

  it('openDetail sets selectedJobId and detailOpen to true', () => {
    useJobStore.getState().openDetail('job-99');
    const state = useJobStore.getState();
    expect(state.selectedJobId).toBe('job-99');
    expect(state.detailOpen).toBe(true);
  });

  it('closeDetail sets detailOpen to false but preserves selectedJobId', () => {
    useJobStore.getState().openDetail('job-99');
    useJobStore.getState().closeDetail();
    const state = useJobStore.getState();
    expect(state.detailOpen).toBe(false);
    expect(state.selectedJobId).toBe('job-99');
  });

  it('resetFilters resets searchQuery, locationFilter, and platformFilters to defaults', () => {
    useJobStore.getState().setSearchQuery('python');
    useJobStore.getState().setLocationFilter('Austin');
    useJobStore.getState().setPlatformFilters(['indeed']);

    useJobStore.getState().resetFilters();
    const state = useJobStore.getState();
    expect(state.searchQuery).toBe('');
    expect(state.locationFilter).toBe('');
    expect(state.platformFilters).toEqual(['linkedin', 'indeed', 'glassdoor']);
  });

  it('resetFilters does not affect selectedJobId or detailOpen', () => {
    useJobStore.getState().openDetail('job-5');
    useJobStore.getState().setSearchQuery('java');

    useJobStore.getState().resetFilters();
    const state = useJobStore.getState();
    expect(state.selectedJobId).toBe('job-5');
    expect(state.detailOpen).toBe(true);
  });

  it('multiple state updates are independent', () => {
    useJobStore.getState().setSearchQuery('golang');
    useJobStore.getState().setLocationFilter('Berlin');
    useJobStore.getState().setPlatformFilters(['glassdoor']);
    useJobStore.getState().openDetail('job-7');

    const state = useJobStore.getState();
    expect(state.searchQuery).toBe('golang');
    expect(state.locationFilter).toBe('Berlin');
    expect(state.platformFilters).toEqual(['glassdoor']);
    expect(state.selectedJobId).toBe('job-7');
    expect(state.detailOpen).toBe(true);
  });
});
