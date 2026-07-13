/** An authenticated user account. */
export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser?: boolean;
}

/** Registration payload. */
export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

/** Access-token response (refresh token is an httpOnly cookie). */
export interface TokenResponse {
  access_token: string;
  token_type: string;
}
