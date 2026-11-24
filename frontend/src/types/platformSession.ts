/** Platforms that accept an imported browser session (backend `SUPPORTED_PLATFORMS`). */
export const SESSION_PLATFORMS = ['linkedin', 'indeed', 'glassdoor'] as const;
export type SessionPlatform = (typeof SESSION_PLATFORMS)[number];

/**
 * A Playwright `storage_state.json`. Only `cookies` (a non-empty list) is required by the backend;
 * the rest (`origins`, …) is passed through untouched.
 */
export interface StorageState {
  cookies: unknown[];
  [key: string]: unknown;
}

/**
 * Cookie-free public view of a stored platform session.
 * Corresponds to the backend `PlatformSessionResponse` Pydantic schema.
 */
export interface PlatformSession {
  platform: string;
  connected: boolean;
  last_verified_at: string | null;
  expires_at: string | null;
}

/** Request body for `POST /platform-sessions/` (backend `PlatformSessionImport`). */
export interface PlatformSessionImport {
  platform: SessionPlatform;
  storage_state: StorageState;
  expires_at?: string | null;
}
