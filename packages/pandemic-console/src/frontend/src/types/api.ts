/**
 * API response types for pandemic-rest integration
 */

export interface ApiResponse<T> {
  status: 'success' | 'error';
  data?: T;
  error?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface UserInfo {
  username: string;
  email?: string;
  full_name?: string;
  roles: string[];
}

export interface HealthResponse {
  status: string;
  daemon?: boolean;
  infection_id?: string;
}

export interface StatusResponse {
  daemon?: string;
  infections?: number;
  uptime?: string;
  infection_id?: string;
  name?: string;
  state?: string;
  systemd_status?: Record<string, any>;
}