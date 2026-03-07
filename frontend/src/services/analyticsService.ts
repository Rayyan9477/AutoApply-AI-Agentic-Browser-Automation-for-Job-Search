import api from './api';
import type {
  DashboardStats,
  ApplicationFunnelData,
  ATSScoreDistribution,
  LLMUsageStats,
  TimelineEntry,
} from '@/types/analytics';

/** Get aggregated dashboard statistics. */
export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>('/analytics/dashboard');
  return data;
}

/** Get application funnel stage counts. */
export async function getApplicationFunnel(): Promise<ApplicationFunnelData[]> {
  const { data } = await api.get<ApplicationFunnelData[]>('/analytics/funnel');
  return data;
}

/** Get ATS score distribution histogram. */
export async function getATSDistribution(): Promise<ATSScoreDistribution[]> {
  const { data } = await api.get<ATSScoreDistribution[]>('/analytics/ats-scores');
  return data;
}

/** Get LLM provider usage statistics. */
export async function getLLMUsage(): Promise<LLMUsageStats[]> {
  const { data } = await api.get<LLMUsageStats[]>('/analytics/llm-usage');
  return data;
}

/** Get daily activity timeline. */
export async function getTimeline(): Promise<TimelineEntry[]> {
  const { data } = await api.get<TimelineEntry[]>('/analytics/timeline');
  return data;
}
