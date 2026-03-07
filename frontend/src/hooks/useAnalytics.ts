import { useQuery } from '@tanstack/react-query';
import * as analyticsService from '@/services/analyticsService';

const ANALYTICS_KEY = ['analytics'] as const;

/** Fetch dashboard statistics. */
export function useDashboardStats() {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'dashboard'],
    queryFn: () => analyticsService.getDashboardStats(),
    refetchInterval: 30_000,
  });
}

/** Fetch the application funnel data. */
export function useApplicationFunnel() {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'funnel'],
    queryFn: () => analyticsService.getApplicationFunnel(),
  });
}

/** Fetch ATS score distribution histogram. */
export function useATSDistribution() {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'ats-scores'],
    queryFn: () => analyticsService.getATSDistribution(),
  });
}

/** Fetch LLM usage statistics. */
export function useLLMUsage() {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'llm-usage'],
    queryFn: () => analyticsService.getLLMUsage(),
  });
}

/** Fetch daily activity timeline. */
export function useTimeline() {
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'timeline'],
    queryFn: () => analyticsService.getTimeline(),
  });
}
