/** Standard API error response shape. */
export interface ApiError {
  detail: string;
  status_code: number;
  /** Machine-readable error code from the backend (e.g. `LLM_BUDGET_EXCEEDED`). */
  code?: string;
  trace_id?: string;
}

/** Generic paginated response wrapper. */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}
