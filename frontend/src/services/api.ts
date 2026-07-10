import axios, { type InternalAxiosRequestConfig } from 'axios';
import type { ApiError } from '@/types/api';
import { useAuthStore } from '@/store/useAuthStore';

/** Pre-configured Axios instance pointing at the backend API. */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30_000,
  // Send the httpOnly refresh cookie on auth requests.
  withCredentials: true,
});

/** Attach a trace-id and the bearer token to every outgoing request. */
api.interceptors.request.use((config) => {
  config.headers['X-Trace-Id'] = crypto.randomUUID();
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

/** Requests to these paths must never trigger a refresh-retry (they ARE the auth flow). */
const isAuthEntry = (url: string): boolean =>
  /\/auth\/(login|register|refresh)/.test(url);

// Single-flight refresh: concurrent 401s share ONE `/auth/refresh` call so we don't stampede
// the endpoint or mint several tokens. Reset once it settles.
let refreshPromise: Promise<string> | null = null;

function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = api
      .post<{ access_token: string }>('/auth/refresh')
      .then((res) => {
        const token = res.data.access_token;
        useAuthStore.setState({ token });
        return token;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

/**
 * Normalize errors. On a 401 for a non-auth request, transparently refresh the access token
 * (via the httpOnly refresh cookie) once and retry the original request; only de-authenticate
 * if the refresh itself fails. This keeps an active session alive past the 15-min access-token
 * expiry instead of bouncing the user to /login.
 */
api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error) || !error.response) {
      const fallback: ApiError = {
        detail: 'Network error. Please check your connection.',
        status_code: 0,
      };
      return Promise.reject(fallback);
    }

    const status = error.response.status;
    const original = error.config as RetriableConfig | undefined;
    const url = original?.url ?? '';

    if (status === 401 && original && !isAuthEntry(url)) {
      if (!original._retried) {
        original._retried = true;
        try {
          const token = await refreshAccessToken();
          original.headers['Authorization'] = `Bearer ${token}`;
          return await api(original);
        } catch {
          useAuthStore.getState().clear();
        }
      } else {
        useAuthStore.getState().clear();
      }
    }

    const data = error.response.data as Record<string, unknown>;
    const apiError: ApiError = {
      detail: typeof data['detail'] === 'string' ? data['detail'] : 'An unexpected error occurred',
      status_code: status,
      trace_id: typeof data['trace_id'] === 'string' ? data['trace_id'] : undefined,
    };
    return Promise.reject(apiError);
  },
);

export default api;
