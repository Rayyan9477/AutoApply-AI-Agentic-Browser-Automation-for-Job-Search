import { create } from 'zustand';

interface JobStoreState {
  /** Currently selected job ID for the detail drawer. */
  selectedJobId: string | null;
  /** Current search query text. */
  searchQuery: string;
  /** Current location filter. */
  locationFilter: string;
  /** Selected platform filters. */
  platformFilters: string[];
  /** Whether the job detail drawer is open. */
  detailOpen: boolean;

  setSelectedJobId: (id: string | null) => void;
  setSearchQuery: (query: string) => void;
  setLocationFilter: (location: string) => void;
  setPlatformFilters: (platforms: string[]) => void;
  openDetail: (jobId: string) => void;
  closeDetail: () => void;
  resetFilters: () => void;
}

export const useJobStore = create<JobStoreState>((set) => ({
  selectedJobId: null,
  searchQuery: '',
  locationFilter: '',
  platformFilters: ['linkedin', 'indeed', 'glassdoor'],
  detailOpen: false,

  setSelectedJobId: (id) => set({ selectedJobId: id }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setLocationFilter: (location) => set({ locationFilter: location }),
  setPlatformFilters: (platforms) => set({ platformFilters: platforms }),
  openDetail: (jobId) => set({ selectedJobId: jobId, detailOpen: true }),
  closeDetail: () => set({ detailOpen: false }),
  resetFilters: () =>
    set({
      searchQuery: '',
      locationFilter: '',
      platformFilters: ['linkedin', 'indeed', 'glassdoor'],
    }),
}));
