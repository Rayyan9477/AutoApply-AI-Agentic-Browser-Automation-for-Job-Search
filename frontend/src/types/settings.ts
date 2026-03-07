/**
 * Current user settings.
 * Corresponds to the backend `SettingsResponse` Pydantic schema.
 */
export interface Settings {
  apply_mode: string;
  min_ats_score: number;
  max_parallel: number;
  platforms_enabled: string[];
  candidate_profile: Record<string, unknown>;
}

/** Alias matching the backend schema name `SettingsResponse`. */
export type SettingsResponse = Settings;

/** Request to update user settings. Only provided fields are changed. */
export interface SettingsUpdate {
  apply_mode?: string;
  min_ats_score?: number;
  max_parallel?: number;
  platforms_enabled?: string[];
  candidate_profile?: Record<string, unknown>;
}

/** Status of a configured LLM provider. */
export interface LLMProviderStatus {
  provider: string;
  configured: boolean;
  model: string;
  is_primary: boolean;
}
