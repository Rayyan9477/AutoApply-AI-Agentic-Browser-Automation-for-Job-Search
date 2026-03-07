/** Standard API error response shape. */
export interface ApiError {
  detail: string;
  status_code: number;
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
