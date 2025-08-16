/**
 * Host system monitoring types
 */

export interface NetworkInterface {
  name: string;
  ipAddress: string;
  status: 'up' | 'down';
  bytesReceived: number;
  bytesSent: number;
}

export interface HostMetrics {
  cpu: {
    usage: number;
    cores: number;
    loadAverage: number[];
  };
  memory: {
    used: number;
    total: number;
    percentage: number;
    available: number;
  };
  disk: {
    used: number;
    total: number;
    percentage: number;
    mountPoint: string;
  };
  network: {
    interfaces: NetworkInterface[];
    connectivity: boolean;
  };
  uptime: string;
  timestamp: string;
}

export interface ActivityEvent {
  id: string;
  type: 'infection_started' | 'infection_stopped' | 'infection_installed' | 'system_alert';
  message: string;
  infectionId?: string;
  severity: 'info' | 'warning' | 'error';
  timestamp: string;
}