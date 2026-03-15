export interface WorkExperience {
  title: string;
  company: string;
  start_date: string;
  end_date: string;
  description: string;
  responsibilities: string[];
}

export interface Education {
  degree: string;
  institution: string;
  graduation_year: string;
  gpa?: string;
}

export interface CandidateProfile {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  linkedin_url: string;
  github_url: string;
  summary: string;
  skills: string[];
  experience: WorkExperience[];
  education: Education[];
  certifications: string[];
}

/**
 * Current user settings.
 * Corresponds to the backend `SettingsResponse` Pydantic schema.
 */
export interface Settings {
  apply_mode: string;
  min_ats_score: number;
  max_parallel: number;
  preferred_provider: string;
  platforms_enabled: string[];
  candidate_profile: CandidateProfile;
}

/** Alias matching the backend schema name `SettingsResponse`. */
export type SettingsResponse = Settings;

/** Request to update user settings. Only provided fields are changed. */
export interface SettingsUpdate {
  apply_mode?: string;
  min_ats_score?: number;
  max_parallel?: number;
  preferred_provider?: string;
  platforms_enabled?: string[];
  candidate_profile?: CandidateProfile;
}

/** Status of a configured LLM provider. */
export interface LLMProviderStatus {
  provider: string;
  configured: boolean;
  model: string;
  is_primary: boolean;
}
