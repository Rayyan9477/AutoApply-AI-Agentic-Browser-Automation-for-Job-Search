import axios from 'axios';
import type { ApiError } from '@/types/api';

/** Pre-configured Axios instance pointing at the backend API. */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30_000,
});

/** Attach a unique trace-id header to every outgoing request. */
api.interceptors.request.use((config) => {
  config.headers['X-Trace-Id'] = crypto.randomUUID();
  return config;
});

/** Normalize error responses into a consistent ApiError shape. */
api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response) {
      const data = error.response.data as Record<string, unknown>;
      const apiError: ApiError = {
        detail: typeof data['detail'] === 'string' ? data['detail'] : 'An unexpected error occurred',
        status_code: error.response.status,
        trace_id:
          typeof data['trace_id'] === 'string' ? data['trace_id'] : undefined,
      };
      return Promise.reject(apiError);
    }
    const fallback: ApiError = {
      detail: 'Network error. Please check your connection.',
      status_code: 0,
    };
    return Promise.reject(fallback);
  },
);

export default api;
