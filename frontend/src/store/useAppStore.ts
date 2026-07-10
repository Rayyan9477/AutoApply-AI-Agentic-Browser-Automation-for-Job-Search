import { create } from 'zustand';

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

interface AppStoreState {
  /** Active notification for the global toaster. */
  notification: Notification | null;
  /** Whether the backend WebSocket is connected. */
  wsConnected: boolean;
  /** A pending CAPTCHA/2FA intervention the user must resolve, or null. */
  pendingIntervention: PendingIntervention | null;

  showNotification: (message: string, severity?: Notification['severity']) => void;
  clearNotification: () => void;
  setWsConnected: (connected: boolean) => void;
  setIntervention: (iv: PendingIntervention) => void;
  clearIntervention: () => void;
}

export const useAppStore = create<AppStoreState>((set) => ({
  notification: null,
  wsConnected: false,
  pendingIntervention: null,

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
}));
