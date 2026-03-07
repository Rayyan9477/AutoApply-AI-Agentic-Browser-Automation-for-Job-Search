import api from './api';
import type { Settings, SettingsUpdate, LLMProviderStatus } from '@/types/settings';

/** Get the current user settings. */
export async function getSettings(): Promise<Settings> {
  const { data } = await api.get<Settings>('/settings/');
  return data;
}

/** Update user settings. Only provided fields are changed. */
export async function updateSettings(update: SettingsUpdate): Promise<Settings> {
  const { data } = await api.put<Settings>('/settings/', update);
  return data;
}

/** List configured LLM providers and their status. */
export async function getLLMProviders(): Promise<LLMProviderStatus[]> {
  const { data } = await api.get<LLMProviderStatus[]>('/settings/llm-providers');
  return data;
}
