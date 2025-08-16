# Pandemic Console - Web Interface

## Overview

Pandemic Console is a web-based infection that provides a modern, responsive dashboard for managing Pandemic edge computing systems. Built with React + TypeScript and React Bootstrap, it offers a user-friendly alternative to the CLI by consuming the pandemic-rest API directly.

The console runs as a FastAPI server serving a built React application, providing real-time monitoring, infection management, and system health visualization through an intuitive web interface.

## Requirements

### Functional Requirements
- [ ] Web-based dashboard for infection management
- [ ] Real-time system health monitoring
- [ ] JWT authentication integration with pandemic-rest
- [ ] Multi-view navigation (Dashboard, Host, Infections, Detail)
- [ ] Infection lifecycle management (install, start, stop, restart, remove)
- [ ] Real-time log streaming via WebSocket
- [ ] System metrics visualization (CPU, memory, disk)
- [ ] Responsive design for desktop and mobile
- [ ] Bulk operations for multiple infections
- [ ] Configuration editing with YAML syntax highlighting

### Non-Functional Requirements
- [ ] Type-safe TypeScript implementation
- [ ] Responsive Bootstrap UI components
- [ ] Real-time updates with <1 second latency
- [ ] Accessible design (WCAG 2.1 AA)
- [ ] Cross-browser compatibility (Chrome, Firefox, Safari, Edge)
- [ ] Mobile-first responsive design
- [ ] Fast load times (<2 seconds initial load)
- [ ] Offline-capable with service worker

### Dependencies
- React + TypeScript for frontend
- React Bootstrap for UI components
- FastAPI for static file serving
- pandemic-rest for API backend
- WebSocket for real-time updates

## Design

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │───▶│ Pandemic Console│───▶│ Pandemic REST   │
│  (React App)    │    │ Static Server   │    │   API Server    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        │              ┌─────────────────┐              │
        └─────────────▶│   WebSocket     │◀─────────────┘
                       │ Real-time Data  │
                       └─────────────────┘
```

### Core Components

#### Frontend Application (React + TypeScript)
- **Navigation System**: Multi-view routing with React Router
- **Authentication**: JWT token management with localStorage
- **API Client**: Typed Axios client for pandemic-rest integration
- **Real-time Updates**: WebSocket service for live data
- **State Management**: React hooks and context for global state

#### Backend Server (FastAPI)
- **Static File Serving**: Serves built React application
- **Health Endpoints**: Basic health check for the console service
- **Configuration**: Configurable host/port binding
- **CORS Support**: Proper CORS headers for development

#### Data Layer
- **Direct API Access**: No proxy - direct calls to pandemic-rest
- **Type Safety**: TypeScript interfaces matching API responses
- **Caching Strategy**: Smart caching with automatic invalidation
- **Error Handling**: Comprehensive error boundaries and retry logic

### User Interface Design

#### Navigation Structure
```
┌─────────────────────────────────────────────────────────────┐
│ 🦠 Pandemic Console    [Dashboard] [Host] [Infections] [User]│
└─────────────────────────────────────────────────────────────┘
```

#### Dashboard View
- **Health Summary Cards**: System status, daemon health, infection count
- **Quick Actions**: Install new infection, bulk operations
- **Activity Feed**: Recent events, state changes, alerts
- **System Overview**: CPU/memory usage, uptime, network status

#### Host View
- **System Metrics**: Real-time CPU, memory, disk usage charts
- **Daemon Status**: Core daemon health, UDS socket status
- **Network Information**: IP addresses, connectivity status
- **System Logs**: Searchable system event log viewer

#### Infections View
- **Infection Table**: Sortable, filterable list with status indicators
- **Bulk Operations**: Multi-select with batch start/stop/restart
- **Install Modal**: Form-based infection installation
- **Quick Actions**: One-click start/stop/restart buttons

#### Infection Detail View
- **Configuration Editor**: YAML editor with syntax highlighting
- **Log Viewer**: Real-time log streaming with search/filter
- **Metrics Dashboard**: Resource usage, restart count, uptime
- **Action Panel**: Start, stop, restart, remove, update operations

### API Integration

#### Authentication Flow
```typescript
interface AuthService {
  login(username: string, password: string): Promise<AuthResponse>;
  logout(): void;
  refreshToken(): Promise<string>;
  isAuthenticated(): boolean;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}
```

#### API Client Structure
```typescript
class PandemicAPI {
  private client: AxiosInstance;
  
  // Authentication
  async login(credentials: LoginRequest): Promise<AuthResponse>;
  
  // Infections
  async getInfections(): Promise<InfectionListResponse>;
  async getInfection(id: string): Promise<InfectionInfo>;
  async installInfection(request: InstallRequest): Promise<InstallResponse>;
  async startInfection(id: string): Promise<ActionResponse>;
  async stopInfection(id: string): Promise<ActionResponse>;
  async restartInfection(id: string): Promise<ActionResponse>;
  async removeInfection(id: string): Promise<void>;
  
  // System
  async getSystemStatus(): Promise<StatusResponse>;
  async getSystemHealth(): Promise<HealthResponse>;
  async getInfectionLogs(id: string, lines?: number): Promise<LogsResponse>;
}
```

#### WebSocket Integration
```typescript
interface WebSocketService {
  connect(): void;
  disconnect(): void;
  subscribe(topic: string, callback: (data: any) => void): void;
  unsubscribe(topic: string): void;
}

// WebSocket message types
interface WSMessage {
  type: 'infection_status' | 'system_metrics' | 'log_entry' | 'activity';
  data: any;
  timestamp: string;
}
```

### TypeScript Interfaces

#### Core Data Types
```typescript
// Infection management
interface Infection {
  infectionId: string;
  name: string;
  state: InfectionState;
  source?: string;
  installationPath?: string;
  serviceName?: string;
  systemdStatus?: SystemdStatus;
  lastUpdated: string;
}

type InfectionState = 'running' | 'stopped' | 'starting' | 'stopping' | 'failed' | 'unknown';

interface SystemdStatus {
  activeState: string;
  pid?: number;
  memoryUsage?: string;
  cpuUsage?: string;
  uptime?: string;
  restartCount?: number;
}

// System monitoring
interface HostMetrics {
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

interface NetworkInterface {
  name: string;
  ipAddress: string;
  status: 'up' | 'down';
  bytesReceived: number;
  bytesSent: number;
}

// Activity tracking
interface ActivityEvent {
  id: string;
  type: 'infection_started' | 'infection_stopped' | 'infection_installed' | 'system_alert';
  message: string;
  infectionId?: string;
  severity: 'info' | 'warning' | 'error';
  timestamp: string;
}
```

## Implementation Details

### Project Structure
```
pandemic-console/
├── src/
│   ├── pandemic_console/          # Python FastAPI server
│   │   ├── __init__.py
│   │   ├── app.py                 # FastAPI application
│   │   ├── service.py             # Systemd service runner
│   │   └── static/                # Built React app (generated)
│   └── frontend/                  # React TypeScript source
│       ├── package.json
│       ├── tsconfig.json
│       ├── webpack.config.js
│       ├── src/
│       │   ├── App.tsx            # Main application component
│       │   ├── index.tsx          # React entry point
│       │   ├── types/             # TypeScript interfaces
│       │   │   ├── api.ts
│       │   │   ├── infection.ts
│       │   │   ├── host.ts
│       │   │   └── websocket.ts
│       │   ├── services/          # API and WebSocket services
│       │   │   ├── api.ts
│       │   │   ├── websocket.ts
│       │   │   └── auth.ts
│       │   ├── hooks/             # Custom React hooks
│       │   │   ├── useAuth.ts
│       │   │   ├── useWebSocket.ts
│       │   │   ├── useApi.ts
│       │   │   └── usePolling.ts
│       │   ├── components/        # Reusable UI components
│       │   │   ├── common/
│       │   │   │   ├── LoadingSpinner.tsx
│       │   │   │   ├── ErrorBoundary.tsx
│       │   │   │   ├── StatusBadge.tsx
│       │   │   │   └── ConfirmModal.tsx
│       │   │   ├── Navigation.tsx
│       │   │   ├── Dashboard/
│       │   │   │   ├── HealthCards.tsx
│       │   │   │   ├── ActivityFeed.tsx
│       │   │   │   ├── QuickStats.tsx
│       │   │   │   └── SystemOverview.tsx
│       │   │   ├── Host/
│       │   │   │   ├── SystemMetrics.tsx
│       │   │   │   ├── MetricsChart.tsx
│       │   │   │   ├── DaemonStatus.tsx
│       │   │   │   └── SystemLogs.tsx
│       │   │   ├── Infections/
│       │   │   │   ├── InfectionList.tsx
│       │   │   │   ├── InfectionCard.tsx
│       │   │   │   ├── InfectionTable.tsx
│       │   │   │   ├── InstallModal.tsx
│       │   │   │   ├── BulkActions.tsx
│       │   │   │   └── FilterBar.tsx
│       │   │   └── InfectionDetail/
│       │   │       ├── ConfigEditor.tsx
│       │   │       ├── LogViewer.tsx
│       │   │       ├── MetricsChart.tsx
│       │   │       ├── ActionButtons.tsx
│       │   │       └── InfoPanel.tsx
│       │   ├── pages/             # Main page components
│       │   │   ├── Dashboard.tsx
│       │   │   ├── Host.tsx
│       │   │   ├── Infections.tsx
│       │   │   ├── InfectionDetail.tsx
│       │   │   └── Login.tsx
│       │   ├── contexts/          # React contexts
│       │   │   ├── AuthContext.tsx
│       │   │   ├── WebSocketContext.tsx
│       │   │   └── ThemeContext.tsx
│       │   └── utils/             # Utility functions
│       │       ├── constants.ts
│       │       ├── helpers.ts
│       │       ├── formatters.ts
│       │       └── validators.ts
│       └── public/
│           ├── index.html
│           ├── favicon.ico
│           └── manifest.json
├── bin/
│   └── pandemic-console           # Executable script
├── infection.yaml                 # Infection definition
├── build.sh                      # Build script
└── README.md
```

### Configuration Format
```yaml
# infection.yaml
metadata:
  name: pandemic-console
  version: 1.0.0
  description: Web-based dashboard for Pandemic edge computing system
  author: Pandemic Team

source:
  type: github
  url: github://pandemic-org/pandemic-console@v1.0.0

systemd:
  user: pandemic-console
  group: pandemic
  working_directory: /opt/pandemic/infections/pandemic-console
  environment:
    PANDEMIC_CONSOLE_CONFIG: "/etc/pandemic/console/config.yaml"

execution:
  command: ./bin/pandemic-console
  restart: always
  restart_sec: 10

resources:
  memory_limit: 512M
  cpu_quota: 25%

security:
  capabilities: []
  read_only_root: false
  no_new_privileges: true

# Console configuration
server:
  host: 0.0.0.0
  port: 3000
  workers: 1

api:
  base_url: https://localhost:8443/api/v1
  timeout: 30
  retry_attempts: 3

websocket:
  url: wss://localhost:8443/api/v1/events
  reconnect_interval: 5000
  max_reconnect_attempts: 10

ui:
  theme: light
  auto_refresh_interval: 5000
  log_lines_default: 100
  log_lines_max: 1000

security:
  session_timeout: 3600
  csrf_protection: true
  content_security_policy: true
```

## Examples

### Installation and Setup
```bash
# 1. Install pandemic-console as infection
pandemic-cli install github://pandemic-org/pandemic-console --name console

# 2. Configure console settings
sudo cp /opt/pandemic/infections/pandemic-console/config.example.yaml /etc/pandemic/console/config.yaml

# 3. Start the console
pandemic-cli start console

# 4. Access web interface
open https://localhost:3000
```

### Component Usage Examples

#### Dashboard Component
```typescript
// pages/Dashboard.tsx
import React from 'react';
import { Container, Row, Col } from 'react-bootstrap';
import { HealthCards } from '../components/Dashboard/HealthCards';
import { ActivityFeed } from '../components/Dashboard/ActivityFeed';
import { QuickStats } from '../components/Dashboard/QuickStats';
import { useApi } from '../hooks/useApi';

export const Dashboard: React.FC = () => {
  const { data: status, loading, error } = useApi('/status');
  const { data: infections } = useApi('/infections');

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <Container fluid>
      <Row className="mb-4">
        <Col>
          <h1>Dashboard</h1>
        </Col>
      </Row>
      
      <Row className="mb-4">
        <Col md={3}>
          <HealthCards status={status} />
        </Col>
        <Col md={6}>
          <QuickStats infections={infections} />
        </Col>
        <Col md={3}>
          <ActivityFeed />
        </Col>
      </Row>
    </Container>
  );
};
```

#### API Service Usage
```typescript
// services/api.ts
import axios, { AxiosInstance } from 'axios';
import { AuthService } from './auth';

class PandemicAPI {
  private client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
    });

    // Add auth interceptor
    this.client.interceptors.request.use((config) => {
      const token = AuthService.getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Add response interceptor for token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          await AuthService.logout();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  async getInfections(): Promise<InfectionListResponse> {
    const response = await this.client.get<InfectionListResponse>('/infections');
    return response.data;
  }

  async startInfection(id: string): Promise<ActionResponse> {
    const response = await this.client.post<ActionResponse>(`/infections/${id}/start`);
    return response.data;
  }
}
```

#### WebSocket Hook
```typescript
// hooks/useWebSocket.ts
import { useEffect, useCallback } from 'react';
import { WebSocketService } from '../services/websocket';

export const useWebSocket = (topic: string, onMessage: (data: any) => void) => {
  const handleMessage = useCallback(onMessage, [onMessage]);

  useEffect(() => {
    WebSocketService.subscribe(topic, handleMessage);
    
    return () => {
      WebSocketService.unsubscribe(topic);
    };
  }, [topic, handleMessage]);
};

// Usage in component
const InfectionList: React.FC = () => {
  const [infections, setInfections] = useState<Infection[]>([]);

  useWebSocket('infection_status', (data) => {
    setInfections(prev => 
      prev.map(inf => 
        inf.infectionId === data.infectionId 
          ? { ...inf, state: data.state }
          : inf
      )
    );
  });

  return (
    // Component JSX
  );
};
```

## Testing

### Test Scenarios
- [ ] Authentication flow (login, logout, token refresh)
- [ ] Navigation between all views
- [ ] Real-time updates via WebSocket
- [ ] Infection management operations
- [ ] Responsive design on different screen sizes
- [ ] Error handling and recovery
- [ ] Performance with large numbers of infections
- [ ] Accessibility compliance

### Testing Strategy
- **Unit Tests**: Jest + React Testing Library for components
- **Integration Tests**: API integration and WebSocket functionality
- **E2E Tests**: Cypress for full user workflows
- **Visual Tests**: Storybook for component documentation
- **Performance Tests**: Lighthouse for web vitals

### Test Structure
```
frontend/src/
├── __tests__/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── hooks/
├── __mocks__/
│   ├── api.ts
│   └── websocket.ts
└── cypress/
    ├── integration/
    ├── fixtures/
    └── support/
```

## Security Considerations

### Authentication Security
- JWT token storage in httpOnly cookies (production)
- Automatic token refresh before expiration
- Secure logout with token invalidation
- Session timeout with user notification

### API Security
- HTTPS-only communication in production
- CORS configuration for allowed origins
- Request timeout and retry limits
- Input validation and sanitization

### Content Security
- Content Security Policy (CSP) headers
- XSS protection with React's built-in escaping
- CSRF protection for state-changing operations
- Secure headers (HSTS, X-Frame-Options)

### Data Protection
- No sensitive data in localStorage
- Secure WebSocket connections (WSS)
- Audit logging for administrative actions
- Rate limiting for API requests

## Deployment

### Build Process
```bash
# Frontend build
cd src/frontend
npm install
npm run build

# Copy built assets to Python static folder
cp -r build/* ../pandemic_console/static/

# Install Python package
pip install -e .
```

### Production Configuration
```yaml
# Production config
server:
  host: 0.0.0.0
  port: 3000
  
api:
  base_url: https://pandemic-rest.local:8443/api/v1
  
security:
  https_only: true
  secure_cookies: true
  csrf_protection: true
```

### Monitoring
```bash
# Check console status
pandemic-cli status console

# View console logs
pandemic-cli logs console

# Test web interface
curl -k https://localhost:3000/health
```

## Migration

### From CLI to Web Interface
1. Install pandemic-console infection
2. Configure API endpoint and authentication
3. Start console service
4. Train users on web interface
5. Monitor usage and performance

### Breaking Changes
- Requires pandemic-rest to be installed and running
- New authentication flow for web users
- Different user experience from CLI

### Rollback Plan
- Stop pandemic-console infection
- Continue using pandemic-cli for management
- Remove web interface dependencies
- Restore CLI-only workflows

## Implementation Plan

### Phase 1: Core Infrastructure
- [ ] FastAPI server setup
- [ ] React + TypeScript project structure
- [ ] Authentication integration
- [ ] Basic navigation and routing
- [ ] API client with error handling

### Phase 2: Dashboard Views
- [ ] Dashboard overview page
- [ ] Host metrics and monitoring
- [ ] Infection list and management
- [ ] Real-time WebSocket integration

### Phase 3: Advanced Features
- [ ] Infection detail views
- [ ] Configuration editing
- [ ] Log streaming and search
- [ ] Bulk operations and workflows

### Phase 4: Polish and Production
- [ ] Responsive design optimization
- [ ] Accessibility improvements
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Documentation and deployment guides

## References

- [React Documentation](https://reactjs.org/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs)
- [React Bootstrap Components](https://react-bootstrap.github.io)
- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files)
- [WebSocket API Standards](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)