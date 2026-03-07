import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as settingsService from '@/services/settingsService';
import type { SettingsUpdate } from '@/types/settings';

const SETTINGS_KEY = ['settings'] as const;

/** Fetch current user settings. */
export function useSettings() {
  return useQuery({
    queryKey: [...SETTINGS_KEY, 'current'],
    queryFn: () => settingsService.getSettings(),
  });
}

/** Update user settings. */
export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (update: SettingsUpdate) => settingsService.updateSettings(update),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: SETTINGS_KEY });
    },
  });
}

/** Fetch LLM provider statuses. */
export function useLLMProviders() {
  return useQuery({
    queryKey: [...SETTINGS_KEY, 'llm-providers'],
    queryFn: () => settingsService.getLLMProviders(),
  });
}
