import api from './api';
import type { PlatformSession, PlatformSessionImport } from '@/types/platformSession';

/** List the current user's connected platform sessions (metadata only; cookies never return). */
export async function listPlatformSessions(): Promise<PlatformSession[]> {
  const { data } = await api.get<PlatformSession[]>('/platform-sessions/');
  return data;
}

/** Import (or replace) a platform login from a Playwright storage_state. Stored encrypted. */
export async function importPlatformSession(body: PlatformSessionImport): Promise<PlatformSession> {
  const { data } = await api.post<PlatformSession>('/platform-sessions/', body);
  return data;
}

/** Disconnect a platform, deleting its stored session. 404 if none was connected. */
export async function deletePlatformSession(platform: string): Promise<void> {
  await api.delete(`/platform-sessions/${encodeURIComponent(platform)}`);
}
