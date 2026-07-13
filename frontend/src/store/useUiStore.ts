import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'dark' | 'light';
export type Density = 'comfortable' | 'compact';

interface UiState {
  theme: Theme;
  density: Density;
  sidebarCollapsed: boolean;
  paletteOpen: boolean;
  toggleTheme: () => void;
  toggleDensity: () => void;
  toggleSidebar: () => void;
  setSidebar: (v: boolean) => void;
  setPaletteOpen: (v: boolean) => void;
}

/** UI/presentation state: theme, density, sidebar. Persisted so the choice survives reloads. */
export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      theme: 'dark',
      density: 'comfortable',
      sidebarCollapsed: false,
      paletteOpen: false,
      toggleTheme: () => set((s) => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })),
      toggleDensity: () =>
        set((s) => ({ density: s.density === 'comfortable' ? 'compact' : 'comfortable' })),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setSidebar: (v) => set({ sidebarCollapsed: v }),
      setPaletteOpen: (v) => set({ paletteOpen: v }),
    }),
    { name: 'autoapply-ui', partialize: (s) => ({ theme: s.theme, density: s.density, sidebarCollapsed: s.sidebarCollapsed }) },
  ),
);

/** Mirror theme + density onto <html> so the CSS-variable tokens cascade to every subtree. */
export function applyUiAttributes(theme: Theme, density: Density): void {
  if (typeof document === 'undefined') return;
  const el = document.documentElement;
  el.setAttribute('data-theme', theme);
  el.setAttribute('data-density', density);
}

// Self-wire: applying the theme is a side effect of importing the store, and it re-applies on change.
if (typeof document !== 'undefined') {
  const sync = () => {
    const { theme, density } = useUiStore.getState();
    applyUiAttributes(theme, density);
  };
  sync();
  useUiStore.subscribe(sync);
}
