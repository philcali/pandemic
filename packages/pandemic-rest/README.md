# Pandemic REST

HTTP REST API infection for Pandemic edge computing system.

## Overview

Pandemic REST is an infection that provides HTTP/REST API access to pandemic-core functionality. It serves as a bridge between the Unix Domain Socket (UDS) interface of the core daemon and standard HTTP clients, enabling web-based management, remote administration, and integration with external systems.

The infection runs as a FastAPI server that communicates with the pandemic-core daemon via UDS, translating HTTP requests to UDS messages and responses back to HTTP.

## Features

- **Complete REST API**: All pandemic-core operations via HTTP endpoints
- **JWT Authentication**: Secure token-based authentication with configurable expiry
- **Role-Based Access Control**: Admin, operator, and read-only permissions
- **Pluggable User Management**: Local files, LDAP, or OIDC authentication
- **HTTPS Support**: TLS termination with configurable certificates
- **CORS Support**: Cross-origin resource sharing for web clients
- **OpenAPI Documentation**: Automatic API docs at `/docs`
- **Real-time Logs**: WebSocket streaming for infection logs
- **Rate Limiting**: Configurable request throttling
- **Audit Logging**: Complete audit trail of API operations

## Installation

### Install as Infection

```bash
# Install pandemic-rest infection
pandemic-cli install github://pandemic-org/pandemic-rest --name rest-api

# Check installation status
pandemic-cli status rest-api
```

### Configure Users and Authentication

1. **Create users file**:
```bash
sudo mkdir -p /etc/pandemic/rest
sudo cp /opt/pandemic/infections/pandemic-rest/users.example.yaml /etc/pandemic/rest/users.yaml
sudo chown pandemic-rest:pandemic /etc/pandemic/rest/users.yaml
sudo chmod 600 /etc/pandemic/rest/users.yaml
```

2. **Generate password hashes**:
```bash
# Generate SHA256 hash for password
echo -n "your-password" | sha256sum

# Example: password "secret123" becomes:
# ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f
```

3. **Edit users file**:
```yaml
# /etc/pandemic/rest/users.yaml
users:
  admin:
    password_hash: "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
    email: admin@company.com
    full_name: System Administrator
    roles:
      - admin
  
  operator:
    password_hash: "5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5"
    email: operator@company.com
    full_name: System Operator
    roles:
      - operator
```

### Configure TLS Certificates

1. **Generate self-signed certificate** (development):
```bash
sudo openssl req -x509 -newkey rsa:4096 -keyout /etc/pandemic/certs/rest-api.key \
  -out /etc/pandemic/certs/rest-api.crt -days 365 -nodes \
  -subj "/C=US/ST=CA/L=San Francisco/O=Pandemic/CN=pandemic-api.local"
```

2. **Set secure permissions**:
```bash
sudo chown pandemic-rest:pandemic /etc/pandemic/certs/rest-api.*
sudo chmod 600 /etc/pandemic/certs/rest-api.*
```

### Configure REST API

1. **Create configuration file**:
```bash
sudo cp /opt/pandemic/infections/pandemic-rest/config.example.yaml /etc/pandemic/rest/config.yaml
sudo chown pandemic-rest:pandemic /etc/pandemic/rest/config.yaml
sudo chmod 600 /etc/pandemic/rest/config.yaml
```

2. **Edit configuration**:
```yaml
# /etc/pandemic/rest/config.yaml
server:
  host: 0.0.0.0
  port: 8443
  workers: 4

tls:
  enabled: true
  cert_file: /etc/pandemic/certs/rest-api.crt
  key_file: /etc/pandemic/certs/rest-api.key

auth:
  jwt_secret: your-secret-key-change-in-production
  jwt_expiry: 3600

user_management:
  provider: local
  local:
    users_file: /etc/pandemic/rest/users.yaml
    role_mapping:
      admin: admin
      operator: operator
      user: read-only

cors:
  enabled: true
  origins:
    - https://pandemic-ui.local
    - https://localhost:3000
```

### Start the REST API

```bash
# Start the REST API infection
pandemic-cli start rest-api

# Check status
pandemic-cli status rest-api

# View logs
pandemic-cli logs rest-api
```

## API Usage

### Base URL
```
https://pandemic-api.local:8443/api/v1/
```

### Authentication

1. **Login to get JWT token**:
```bash
curl -k -X POST https://localhost:8443/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret123"}'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

2. **Use token in subsequent requests**:
```bash
curl -k https://localhost:8443/api/v1/infections \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### API Endpoints

#### Health and Status
```bash
# Health check (public, no authentication)
GET /api/v1/health

# Daemon status (authenticated)
GET /api/v1/status

# Specific infection status
GET /api/v1/status?infection_id=infection-123
```

#### Infection Management
```bash
# List all infections
GET /api/v1/infections

# Filter by state
GET /api/v1/infections?state=running

# Get specific infection
GET /api/v1/infections/{infection_id}

# Install new infection (admin/operator only)
POST /api/v1/infections
{
  "source": "github://org/repo@v1.0.0",
  "name": "my-infection",
  "config_overrides": {
    "environment": {"DEBUG": "true"},
    "resources": {"memoryLimit": "512M"}
  }
}

# Remove infection (admin/operator only)
DELETE /api/v1/infections/{infection_id}?cleanup=true

# Start infection (admin/operator only)
POST /api/v1/infections/{infection_id}/start

# Stop infection (admin/operator only)
POST /api/v1/infections/{infection_id}/stop

# Restart infection (admin/operator only)
POST /api/v1/infections/{infection_id}/restart

# Get infection logs
GET /api/v1/infections/{infection_id}/logs?lines=100
```

#### User Information
```bash
# Get current user info
GET /api/v1/auth/me

# Logout (client should discard token)
POST /api/v1/auth/logout
```

### Python Client Example

```python
import httpx

class PandemicAPI:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.client = httpx.Client(verify=False)  # Disable SSL verification for self-signed certs
        self.token = None
        self._login(username, password)
    
    def _login(self, username, password):
        """Authenticate and get JWT token."""
        response = self.client.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
    
    def _headers(self):
        """Get authorization headers."""
        return {"Authorization": f"Bearer {self.token}"}
    
    def list_infections(self):
        """List all infections."""
        response = self.client.get(
            f"{self.base_url}/api/v1/infections",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    def install_infection(self, source, name=None):
        """Install new infection."""
        payload = {"source": source}
        if name:
            payload["name"] = name
        
        response = self.client.post(
            f"{self.base_url}/api/v1/infections",
            json=payload,
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    def start_infection(self, infection_id):
        """Start infection."""
        response = self.client.post(
            f"{self.base_url}/api/v1/infections/{infection_id}/start",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

# Usage
api = PandemicAPI("https://localhost:8443", "admin", "secret123")
infections = api.list_infections()
print(f"Found {len(infections['infections'])} infections")
```

### JavaScript/Web Client Example

```javascript
class PandemicAPI {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.token = null;
  }
  
  async login(username, password) {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (!response.ok) throw new Error('Login failed');
    
    const data = await response.json();
    this.token = data.access_token;
    return data;
  }
  
  async listInfections() {
    const response = await fetch(`${this.baseUrl}/api/v1/infections`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    
    if (!response.ok) throw new Error('Failed to list infections');
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
    
    if (!response.ok) throw new Error('Failed to install infection');
    return response.json();
  }
}

// Usage
const api = new PandemicAPI('https://localhost:8443');
await api.login('admin', 'secret123');
const infections = await api.listInfections();
console.log(`Found ${infections.infections.length} infections`);
```

## User Management

### Local Users (Default)

Local users are stored in a YAML file with SHA256 password hashes:

```yaml
# /etc/pandemic/rest/users.yaml
users:
  username:
    password_hash: "sha256_hash_of_password"
    email: user@company.com
    full_name: User Full Name
    roles:
      - admin      # Full access
      - operator   # Install/manage infections
      - read-only  # View-only access
```

**Generate password hash**:
```bash
echo -n "your-password" | sha256sum
```

### LDAP Integration

Configure LDAP authentication in the main config:

```yaml
# /etc/pandemic/rest/config.yaml
user_management:
  provider: ldap
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
```

### OIDC/OAuth2 Integration

Configure OIDC authentication:

```yaml
# /etc/pandemic/rest/config.yaml
user_management:
  provider: oidc
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
```

## Role-Based Access Control

### Roles and Permissions

| Role | Permissions |
|------|-------------|
| `admin` | Full access: install, remove, start, stop, restart, view logs, manage users |
| `operator` | Manage infections: install, start, stop, restart, view logs |
| `read-only` | View only: list infections, view status, view logs |

### API Endpoint Permissions

| Endpoint | Admin | Operator | Read-Only |
|----------|-------|----------|-----------|
| `GET /health` | ✅ (public) | ✅ (public) | ✅ (public) |
| `GET /status` | ✅ | ✅ | ✅ |
| `GET /infections` | ✅ | ✅ | ✅ |
| `GET /infections/{id}` | ✅ | ✅ | ✅ |
| `GET /infections/{id}/logs` | ✅ | ✅ | ✅ |
| `POST /infections` | ✅ | ✅ | ❌ |
| `DELETE /infections/{id}` | ✅ | ✅ | ❌ |
| `POST /infections/{id}/start` | ✅ | ✅ | ❌ |
| `POST /infections/{id}/stop` | ✅ | ✅ | ❌ |
| `POST /infections/{id}/restart` | ✅ | ✅ | ❌ |

## Security

### HTTPS Configuration

Always use HTTPS in production:

```yaml
tls:
  enabled: true
  cert_file: /etc/pandemic/certs/rest-api.crt
  key_file: /etc/pandemic/certs/rest-api.key
```

### JWT Security

- Use a strong, random JWT secret
- Configure appropriate token expiry (default: 1 hour)
- Tokens are stateless and cannot be revoked before expiry

```yaml
auth:
  jwt_secret: "use-a-strong-random-secret-key"
  jwt_expiry: 3600  # 1 hour
```

### Rate Limiting

Configure rate limiting to prevent abuse:

```yaml
security:
  rate_limit: 100/minute
  max_request_size: 10MB
```

### File Permissions

Ensure secure file permissions:

```bash
# Configuration files
sudo chmod 600 /etc/pandemic/rest/config.yaml
sudo chmod 600 /etc/pandemic/rest/users.yaml

# TLS certificates
sudo chmod 600 /etc/pandemic/certs/rest-api.key
sudo chmod 644 /etc/pandemic/certs/rest-api.crt

# Ownership
sudo chown -R pandemic-rest:pandemic /etc/pandemic/rest/
sudo chown pandemic-rest:pandemic /etc/pandemic/certs/rest-api.*
```

## Monitoring and Logging

### Health Monitoring

```bash
# Check REST API health
curl -k https://localhost:8443/api/v1/health

# Check via pandemic CLI
pandemic-cli status rest-api
pandemic-cli logs rest-api
```

### Audit Logging

All API operations are logged to the audit log:

```yaml
logging:
  level: INFO
  access_log: true
  audit_log: /var/log/pandemic/rest-audit.log
```

### Metrics

Access built-in FastAPI metrics and OpenAPI documentation:

- **API Documentation**: `https://localhost:8443/docs`
- **Alternative Docs**: `https://localhost:8443/redoc`

## Troubleshooting

### Common Issues

#### Connection Refused
```
Error: Connection refused to https://localhost:8443
```
**Solution**: Check if the REST API infection is running:
```bash
pandemic-cli status rest-api
pandemic-cli start rest-api
```

#### Authentication Failed
```
Error: 401 Unauthorized
```
**Solution**: Check username/password and JWT token:
```bash
# Verify user exists in users.yaml
sudo cat /etc/pandemic/rest/users.yaml

# Check password hash
echo -n "your-password" | sha256sum
```

#### Permission Denied
```
Error: 403 Forbidden
```
**Solution**: Check user roles and endpoint permissions:
```bash
# Get current user info
curl -k https://localhost:8443/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### SSL Certificate Issues
```
Error: SSL certificate verification failed
```
**Solution**: For self-signed certificates, use `-k` flag or disable SSL verification:
```bash
curl -k https://localhost:8443/api/v1/health
```

### Log Analysis

```bash
# View REST API logs
pandemic-cli logs rest-api

# View audit logs
sudo tail -f /var/log/pandemic/rest-audit.log

# View systemd logs
sudo journalctl -u pandemic-infection@rest-api.service -f
```

## Development

### Running Tests

```bash
cd packages/pandemic-rest
pytest tests/
```

### Local Development

```bash
# Install in development mode
pip install -e "packages/pandemic-rest[dev]"

# Run with development config
PANDEMIC_REST_CONFIG=config.dev.yaml python -m pandemic_rest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.