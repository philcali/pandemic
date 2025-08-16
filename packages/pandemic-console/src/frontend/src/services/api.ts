/**
 * API client for pandemic-rest integration
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { 
  AuthResponse, 
  LoginRequest, 
  UserInfo, 
  HealthResponse, 
  StatusResponse
} from '../types/api';
import { 
  InfectionListResponse,
  Infection,
  InstallRequest,
  InstallResponse,
  ActionResponse,
  LogsResponse
} from '../types/infection';

class PandemicAPI {
  private client: AxiosInstance;

  constructor(baseURL: string = process.env.REACT_APP_API_BASE || 'https://localhost:8443/api/v1') {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      }
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('pandemic_auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Clear auth and redirect to login
          localStorage.removeItem('pandemic_auth_token');
          localStorage.removeItem('pandemic_user_info');
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await this.client.post('/auth/login', credentials);
    return response.data;
  }

  async getCurrentUser(): Promise<UserInfo> {
    const response: AxiosResponse<UserInfo> = await this.client.get('/auth/me');
    return response.data;
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout');
    } catch (error) {
      // Ignore logout errors
      console.warn('Logout request failed:', error);
    }
  }

  // System health and status
  async getHealth(): Promise<HealthResponse> {
    const response: AxiosResponse<HealthResponse> = await this.client.get('/health');
    return response.data;
  }

  async getStatus(): Promise<StatusResponse> {
    const response: AxiosResponse<StatusResponse> = await this.client.get('/status');
    return response.data;
  }

  // Infection management
  async getInfections(): Promise<InfectionListResponse> {
    const response: AxiosResponse<InfectionListResponse> = await this.client.get('/infections');
    return response.data;
  }

  async getInfection(id: string): Promise<Infection> {
    const response: AxiosResponse<Infection> = await this.client.get(`/infections/${id}`);
    return response.data;
  }

  async installInfection(request: InstallRequest): Promise<InstallResponse> {
    const response: AxiosResponse<InstallResponse> = await this.client.post('/infections', request);
    return response.data;
  }

  async removeInfection(id: string, cleanup: boolean = true): Promise<void> {
    await this.client.delete(`/infections/${id}?cleanup=${cleanup}`);
  }

  async startInfection(id: string): Promise<ActionResponse> {
    const response: AxiosResponse<ActionResponse> = await this.client.post(`/infections/${id}/start`);
    return response.data;
  }

  async stopInfection(id: string): Promise<ActionResponse> {
    const response: AxiosResponse<ActionResponse> = await this.client.post(`/infections/${id}/stop`);
    return response.data;
  }

  async restartInfection(id: string): Promise<ActionResponse> {
    const response: AxiosResponse<ActionResponse> = await this.client.post(`/infections/${id}/restart`);
    return response.data;
  }

  async getInfectionLogs(id: string, lines: number = 100): Promise<LogsResponse> {
    const response: AxiosResponse<LogsResponse> = await this.client.get(`/infections/${id}/logs?lines=${lines}`);
    return response.data;
  }
}

// Export singleton instance
export const api = new PandemicAPI();
export default api;