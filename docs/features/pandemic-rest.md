# Pandemic REST - HTTP API Plugin

## Overview

Pandemic REST is a plugin that provides HTTP/REST API access to pandemic-core functionality. It serves as a bridge between the Unix Domain Socket (UDS) interface of the core daemon and standard HTTP clients, enabling web-based management, remote administration, and integration with external systems.

The plugin runs as a separate HTTP server that communicates with the pandemic-core daemon via UDS, translating HTTP requests to UDS messages and responses back to HTTP.

## Requirements

### Functional Requirements
- [ ] HTTP server with REST API endpoints
- [ ] Translate HTTP requests to UDS protocol messages
- [ ] Support all core daemon operations (install, start, stop, status, logs)
- [ ] JSON request/response format
- [ ] Authentication and authorization
- [ ] CORS support for web clients
- [ ] WebSocket support for real-time updates
- [ ] API versioning (v1 initially)
- [ ] Health check and metrics endpoints

### Non-Functional Requirements
- [ ] High performance with async HTTP handling
- [ ] Secure by default (HTTPS, authentication)
- [ ] Configurable bind address and port
- [ ] Request/response logging and metrics
- [ ] Rate limiting and request validation
- [ ] Graceful shutdown and error handling

### Dependencies
- FastAPI or similar async HTTP framework
- UDS client for pandemic-core communication
- Authentication middleware (JWT, API keys)
- CORS middleware for web clients

## Design

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HTTP Client   │───▶│  Pandemic REST  │───▶│ Pandemic Core   │
│  (Web/Mobile)   │    │   HTTP Server   │    │  UDS Daemon     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Authentication │───▶│ User Management │
                       │   & Security    │    │   (LDAP/OIDC)   │
                       └─────────────────┘    └─────────────────┘
```

### Core Components

#### HTTP Server
- **FastAPI Application**: Async HTTP server with automatic OpenAPI docs
- **Middleware Stack**: Authentication, CORS, logging, rate limiting
- **Route Handlers**: REST endpoints for each daemon operation
- **WebSocket Handler**: Real-time event streaming

#### UDS Client
- **Connection Pool**: Persistent connections to pandemic-core
- **Message Translation**: HTTP ↔ UDS protocol conversion
- **Error Handling**: UDS errors mapped to HTTP status codes
- **Connection Recovery**: Automatic reconnection on failures

#### Authentication System
- **JWT Tokens**: Stateless authentication with configurable expiry
- **API Keys**: Long-lived tokens for service-to-service auth
- **Abstract User Management**: Pluggable user providers (LDAP, OIDC, local)
- **Role-Based Access**: Scopes from user management (admin, operator, read-only)
- **Rate Limiting**: Per-user/IP request throttling

#### User Management System
- **Abstract Provider**: Pluggable user authentication backends
- **LDAP Provider**: Active Directory/OpenLDAP integration
- **OIDC Provider**: OAuth2/OpenID Connect support
- **Local Provider**: File-based users for development
- **Role Mapping**: User groups/roles to pandemic scopes

#### Security Layer
- **HTTPS Only**: TLS termination with configurable certificates
- **Input Validation**: Request schema validation and sanitization
- **CORS Policy**: Configurable cross-origin resource sharing
- **Security Headers**: HSTS, CSP, X-Frame-Options

### API Design

#### Base URL Structure
```
https://pandemic-api.local:8443/api/v1/
```

#### Authentication Endpoints
```http
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
```

#### Core Management Endpoints
```http
GET    /api/v1/health
GET    /api/v1/status
GET    /api/v1/infections
POST   /api/v1/infections
GET    /api/v1/infections/{id}
DELETE /api/v1/infections/{id}
POST   /api/v1/infections/{id}/start
POST   /api/v1/infections/{id}/stop
POST   /api/v1/infections/{id}/restart
GET    /api/v1/infections/{id}/logs
GET    /api/v1/infections/{id}/metrics
```

#### WebSocket Endpoints
```http
WS /api/v1/events
WS /api/v1/infections/{id}/logs/stream
```

### API Examples

#### Authentication
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "secure-password"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### List Infections
```http
GET /api/v1/infections
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

Response:
{
  "infections": [
    {
      "infectionId": "infection-abc123",
      "name": "motion-detector",
      "state": "running",
      "source": "github://pandemic-org/motion-detector@v1.0.0",
      "installationPath": "/opt/pandemic/infections/motion-detector"
    }
  ],
  "totalCount": 1,
  "runningCount": 1
}
```

#### Install Infection
```http
POST /api/v1/infections
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
Content-Type: application/json

{
  "source": "github://pandemic-org/motion-detector@v2.0.0",
  "name": "motion-detector-v2",
  "configOverrides": {
    "environment": {
      "DEBUG": "true"
    },
    "resources": {
      "memoryLimit": "512M"
    }
  }
}

Response:
{
  "infectionId": "infection-def456",
  "serviceName": "pandemic-infection@motion-detector-v2.service",
  "installationPath": "/opt/pandemic/infections/motion-detector-v2"
}
```

#### Get Infection Status
```http
GET /api/v1/infections/infection-abc123
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

Response:
{
  "infectionId": "infection-abc123",
  "name": "motion-detector",
  "state": "running",
  "systemdStatus": {
    "activeState": "active",
    "pid": 12345,
    "memoryUsage": "64.2MB",
    "cpuUsage": "2.1%",
    "uptime": "2h 15m"
  }
}
```

#### Stream Logs (WebSocket)
```javascript
const ws = new WebSocket('wss://pandemic-api.local:8443/api/v1/infections/infection-abc123/logs/stream');
ws.onmessage = (event) => {
  const logEntry = JSON.parse(event.data);
  console.log(`${logEntry.timestamp}: ${logEntry.message}`);
};
```

### Configuration

```yaml
# /etc/pandemic/rest.yaml
server:
  host: 0.0.0.0
  port: 8443
  workers: 4
  
tls:
  enabled: true
  cert_file: /etc/pandemic/certs/api.crt
  key_file: /etc/pandemic/certs/api.key
  
daemon:
  socket_path: /var/run/pandemic.sock
  connection_pool_size: 10
  request_timeout: 30
  
auth:
  jwt_secret: ${JWT_SECRET}
  jwt_expiry: 3600
  api_keys_file: /etc/pandemic/api-keys.yaml
  
user_management:
  provider: ldap  # local, ldap, oidc
  
  # LDAP configuration
  ldap:
    server: ldap://ldap.company.com:389
    bind_dn: cn=pandemic,ou=service,dc=company,dc=com
    bind_password: ${LDAP_PASSWORD}
    user_base: ou=users,dc=company,dc=com
    user_filter: (uid={username})
    group_base: ou=groups,dc=company,dc=com
    group_filter: (member={user_dn})
    role_mapping:
      pandemic-admins: admin
      pandemic-operators: operator
      pandemic-users: read-only
  
  # OIDC configuration  
  oidc:
    issuer: https://auth.company.com
    client_id: pandemic-rest
    client_secret: ${OIDC_CLIENT_SECRET}
    scopes: [openid, profile, groups]
    role_claim: groups
    role_mapping:
      pandemic-admins: admin
      pandemic-operators: operator
      pandemic-users: read-only
  
  # Local users (development only)
  local:
    users_file: /etc/pandemic/users.yaml
  
cors:
  enabled: true
  origins: 
    - https://pandemic-ui.local
    - https://localhost:3000
  
security:
  rate_limit: 100/minute
  max_request_size: 10MB
  
logging:
  level: INFO
  access_log: true
  audit_log: /var/log/pandemic/rest-audit.log
```

## Implementation Details

### Package Structure
```
pandemic-rest/
├── src/
│   ├── pandemic_rest/
│   │   ├── __init__.py
│   │   ├── app.py              # FastAPI application
│   │   ├── auth.py             # Authentication middleware
│   │   ├── client.py           # UDS client wrapper
│   │   ├── users/              # User management providers
│   │   │   ├── __init__.py
│   │   │   ├── base.py         # Abstract user provider
│   │   │   ├── local.py        # Local file-based users
│   │   │   ├── ldap.py         # LDAP/AD integration
│   │   │   └── oidc.py         # OIDC/OAuth2 provider
│   │   ├── routes/             # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # Auth endpoints
│   │   │   ├── infections.py   # Infection management
│   │   │   ├── health.py       # Health/status endpoints
│   │   │   └── websocket.py    # WebSocket handlers
│   │   ├── middleware/         # HTTP middleware
│   │   │   ├── __init__.py
│   │   │   ├── cors.py         # CORS handling
│   │   │   ├── logging.py      # Request logging
│   │   │   └── security.py     # Security headers
│   │   └── models/             # Pydantic models
│   │       ├── __init__.py
│   │       ├── auth.py         # Auth request/response models
│   │       └── infections.py   # Infection models
│   └── tests/
└── pyproject.toml
```

### Dependencies
```toml
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.0.0",
    "python-jose[cryptography]>=3.3.0",
    "python-multipart>=0.0.6",
    "pandemic-common==0.0.1"
]
```

## Examples

### Python Client Usage
```python
import httpx

# Authenticate
auth_response = httpx.post("https://pandemic-api.local:8443/api/v1/auth/login", 
                          json={"username": "admin", "password": "password"})
token = auth_response.json()["access_token"]

# Install infection
headers = {"Authorization": f"Bearer {token}"}
install_response = httpx.post("https://pandemic-api.local:8443/api/v1/infections",
                             headers=headers,
                             json={"source": "github://org/repo@v1.0.0"})
infection_id = install_response.json()["infectionId"]

# Start infection
httpx.post(f"https://pandemic-api.local:8443/api/v1/infections/{infection_id}/start",
           headers=headers)
```

### JavaScript/Web Client
```javascript
class PandemicAPI {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.token = token;
  }
  
  async listInfections() {
    const response = await fetch(`${this.baseUrl}/api/v1/infections`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    return response.json();
  }
  
  async installInfection(source, name) {
    const response = await fetch(`${this.baseUrl}/api/v1/infections`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ source, name })
    });
    return response.json();
  }
}
```

## Testing

### Test Scenarios
- [ ] HTTP endpoint functionality
- [ ] Authentication and authorization
- [ ] UDS communication and error handling
- [ ] WebSocket connections and streaming
- [ ] Rate limiting and security
- [ ] CORS and security headers
- [ ] Performance under load
- [ ] Error conditions and recovery

### Integration Testing
- [ ] End-to-end API workflows
- [ ] Authentication token lifecycle
- [ ] WebSocket event streaming
- [ ] Concurrent request handling
- [ ] UDS connection recovery

## Security Considerations

### Authentication & Authorization
- JWT tokens with configurable expiry
- API key support for service accounts
- Role-based access control (RBAC)
- Secure password hashing (bcrypt)

### Network Security
- HTTPS only with strong TLS configuration
- Configurable CORS policies
- Security headers (HSTS, CSP, etc.)
- Rate limiting per user/IP

### Input Validation
- Pydantic models for request validation
- SQL injection prevention (no SQL used)
- Path traversal protection
- Request size limits

## Deployment

### Systemd Service
```ini
[Unit]
Description=Pandemic REST API Server
After=pandemic.service
Requires=pandemic.service

[Service]
Type=exec
User=pandemic-rest
Group=pandemic
ExecStart=/opt/pandemic/rest/bin/pandemic-rest
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Docker Container
```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -e .
EXPOSE 8443
CMD ["pandemic-rest"]
```

## Migration

### Breaking Changes
- New HTTP API requires client updates
- Authentication tokens need to be managed
- CORS policies may affect web clients

### Migration Steps
1. Install pandemic-rest package
2. Configure TLS certificates and authentication
3. Update client applications to use HTTP API
4. Test authentication and authorization
5. Monitor performance and security

## References

- FastAPI Documentation
- JWT Authentication Best Practices
- REST API Design Guidelines
- WebSocket Protocol Specification
- OWASP API Security Guidelines