import api from './api';
import type { SystemIssue } from '@/types/admin';

/** List recent harness-detected system issues (superuser-only). */
export async function listSystemIssues(status?: string, limit = 100): Promise<SystemIssue[]> {
  const params: Record<string, string | number> = { limit };
  if (status) params['status'] = status;
  const { data } = await api.get<SystemIssue[]>('/admin/system-issues', { params });
  return data;
}
