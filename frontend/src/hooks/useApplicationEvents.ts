import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { WSMessage } from '@/hooks/useWebSocket';
import { useAppStore, type PendingIntervention } from '@/store/useAppStore';

/**
 * Reacts to real-time WebSocket events: `application_progress` invalidates the cached
 * application queries (live status), and `intervention_required` raises a notification
 * prompting the user to resolve a CAPTCHA/2FA challenge.
 */
export function useApplicationEvents(lastMessage: WSMessage | null): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.type === 'application_progress') {
      void queryClient.invalidateQueries({ queryKey: ['applications'] });
    } else if (lastMessage.type === 'intervention_required') {
      const iv = lastMessage.payload as unknown as PendingIntervention;
      useAppStore.getState().setIntervention(iv);
      useAppStore
        .getState()
        .showNotification('A job application needs your input (CAPTCHA/2FA).', 'warning');
    }
  }, [lastMessage, queryClient]);
}
