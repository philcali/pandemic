/**
 * Infection-related types
 */

export type InfectionState = 'running' | 'stopped' | 'starting' | 'stopping' | 'failed' | 'unknown';

export interface SystemdStatus {
  activeState: string;
  pid?: number;
  memoryUsage?: string;
  cpuUsage?: string;
  uptime?: string;
  restartCount?: number;
}

export interface Infection {
  infectionId: string;
  name: string;
  state: InfectionState;
  source?: string;
  installationPath?: string;
  serviceName?: string;
  systemdStatus?: SystemdStatus;
  lastUpdated?: string;
}

export interface InfectionListResponse {
  infections: Infection[];
  totalCount: number;
  runningCount: number;
}

export interface InstallRequest {
  source: string;
  name?: string;
  config_overrides?: Record<string, any>;
}

export interface InstallResponse {
  infection_id: string;
  service_name: string;
  installation_path: string;
}

export interface ActionResponse {
  status: string;
  infection_id: string;
  message?: string;
}

export interface LogsResponse {
  infection_id: string;
  logs: string[];
  lines: number;
}