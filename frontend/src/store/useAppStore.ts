import { create } from 'zustand';

import type { BoardResult, BoardStatus } from '@/types/job';

interface Notification {
  id: string;
  message: string;
  severity: 'success' | 'error' | 'warning' | 'info';
}

/** A human-in-the-loop challenge the agent hit (CAPTCHA/2FA), awaiting the user's response. */
export interface PendingIntervention {
  application_id: string;
  kind: string;
  prompt: string;
}

/** A background board search: per-platform state, keyed by the backend `search_id`. */
export interface BoardSearch {
  searchId: string;
  boards: Record<string, BoardResult>;
}

interface AppStoreState {
  /** Active notification for the global toaster. */
  notification: Notification | null;
  /** Whether the backend WebSocket is connected. */
  wsConnected: boolean;
  /** A pending CAPTCHA/2FA intervention the user must resolve, or null. */
  pendingIntervention: PendingIntervention | null;
  /** The latest background board search (survives navigation), or null. */
  boardSearch: BoardSearch | null;

  showNotification: (message: string, severity?: Notification['severity']) => void;
  clearNotification: () => void;
  setWsConnected: (connected: boolean) => void;
  setIntervention: (iv: PendingIntervention) => void;
  clearIntervention: () => void;
  setBoardSearch: (searchId: string, boards: Record<string, BoardResult>) => void;
  /** Update one board; ignored when `searchId` is not the current search. */
  applyBoardProgress: (
    searchId: string,
    platform: string,
    status: BoardStatus,
    count?: number,
    error?: string | null,
  ) => void;
  clearBoardSearch: () => void;
}

export const useAppStore = create<AppStoreState>((set) => ({
  notification: null,
  wsConnected: false,
  pendingIntervention: null,
  boardSearch: null,

  showNotification: (message, severity = 'info') =>
    set({
      notification: {
        id: crypto.randomUUID(),
        message,
        severity,
      },
    }),

  clearNotification: () => set({ notification: null }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
  setIntervention: (iv) => set({ pendingIntervention: iv }),
  clearIntervention: () => set({ pendingIntervention: null }),
  setBoardSearch: (searchId, boards) => set({ boardSearch: { searchId, boards } }),
  applyBoardProgress: (searchId, platform, status, count, error) =>
    set((s) =>
      s.boardSearch && s.boardSearch.searchId === searchId
        ? {
            boardSearch: {
              searchId,
              boards: { ...s.boardSearch.boards, [platform]: { status, count, error } },
            },
          }
        : s,
    ),
  clearBoardSearch: () => set({ boardSearch: null }),
}));
