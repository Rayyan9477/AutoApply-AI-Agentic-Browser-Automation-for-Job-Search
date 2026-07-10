import { useQuery } from '@tanstack/react-query';

import * as adminService from '@/services/adminService';

/** Poll harness-detected system issues (superuser health view). */
export function useSystemIssues(status?: string) {
  return useQuery({
    queryKey: ['admin', 'system-issues', status],
    queryFn: () => adminService.listSystemIssues(status),
    refetchInterval: 30_000,
  });
}
