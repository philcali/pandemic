# Pandemic IAM - IMDSv2-Style Cloud Metadata Service

## Overview

Pandemic IAM is an infection that provides an IMDSv2-style metadata service for cloud credentials, making cloud authentication transparently available to the entire host. It runs as a FastAPI server on the standard AWS IMDS address (169.254.169.254:80) and exchanges X.509 certificates for temporary cloud credentials.

The service provides host-wide cloud access similar to EC2 instances, allowing any application to discover and use cloud credentials without configuration, while maintaining security through certificate-based authentication with cloud providers.

## Requirements

### Functional Requirements
- [x] IMDSv2-compatible HTTP metadata service
- [x] Certificate-based authentication to cloud providers
- [x] Support multiple cloud providers (AWS, Azure, GCP)
- [x] Exchange certificates for temporary cloud credentials
- [x] Token-based security (IMDSv2 style)
- [x] Automatic credential refresh and caching
- [x] Configurable metadata server endpoint
- [x] Host-wide credential availability
- [x] Audit all authentication operations

### Non-Functional Requirements
- [x] High performance with async HTTP handling
- [x] Secure by default (token-based access)
- [x] Low latency credential operations (<100ms)
- [x] Automatic credential caching and refresh
- [x] Comprehensive audit trail
- [x] Zero-configuration for applications

### Dependencies
- FastAPI for HTTP server
- Cloud provider certificate authentication
- X.509 certificate management
- Pandemic core daemon for infection lifecycle

## Design

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │───▶│  Pandemic IAM   │───▶│ Cloud Provider  │
│ (AWS CLI/SDK)   │    │ Metadata Server │    │  IAM Anywhere   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        │              ┌─────────────────┐              │
        └─────────────▶│ 169.254.169.254 │◀─────────────┘
                       │   IMDSv2 API    │
                       └─────────────────┘
```

### Core Components

#### IMDSv2 Metadata Server
- **FastAPI HTTP Server**: Async server on 169.254.169.254:80
- **Token-Based Security**: PUT /latest/api/token for session tokens
- **Credential Endpoints**: /latest/meta-data/iam/security-credentials/
- **Provider Support**: AWS, Azure, GCP credential formats
- **Automatic Caching**: Credential refresh before expiration

#### Certificate Manager
- **X.509 Certificate Loading**: PEM format certificate validation
- **Unix File Permissions**: Secure 600/400 permission enforcement
- **Certificate Chain Verification**: Trust anchor validation
- **Automatic Renewal**: Certificate expiration monitoring

#### Cloud Provider Adapters
- **AWS Adapter**: IAM Roles Anywhere with request signing
- **Azure Adapter**: Certificate-based managed identity (planned)
- **GCP Adapter**: Workload identity federation (planned)
- **Unified Interface**: Consistent credential format

### IMDSv2 API Design

#### Authentication Flow
```bash
# 1. Get session token (required for all requests)
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-pandemic-token-ttl-seconds: 21600")

# 2. List available providers
curl -H "X-pandemic-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/

# 3. Get credentials for specific provider
curl -H "X-pandemic-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/aws
```

#### API Endpoints

**Token Management**
```http
PUT /latest/api/token
X-pandemic-token-ttl-seconds: 21600

Response: session-token-string
```

**Provider Discovery**
```http
GET /latest/meta-data/iam/security-credentials/
X-pandemic-token: session-token

Response: aws\nazure\ngcp
```

**Credential Retrieval**
```http
GET /latest/meta-data/iam/security-credentials/{provider}
X-pandemic-token: session-token

Response (AWS format):
{
  "Code": "Success",
  "LastUpdated": "2024-01-01T12:00:00Z",
  "Type": "AWS-HMAC",
  "AccessKeyId": "ASIA...",
  "SecretAccessKey": "...",
  "Token": "...",
  "Expiration": "2024-01-01T18:00:00Z"
}
```

**Instance Metadata**
```http
GET /latest/meta-data/instance-id
X-pandemic-token: session-token

Response: pandemic-abc123def456
```

### Implementation Details

#### Infection Structure
```
pandemic-iam/
├── src/
│   ├── pandemic_iam/
│   │   ├── __init__.py
│   │   ├── manager.py         # IAM credential manager
│   │   ├── metadata_server.py # IMDSv2 HTTP server
│   │   ├── service.py         # Systemd service runner
│   │   └── providers/         # Cloud provider adapters
│   │       ├── __init__.py
│   │       ├── base.py        # Abstract provider
│   │       ├── aws.py         # AWS IAM Roles Anywhere
│   │       └── aws_signer.py  # AWS request signing
│   └── tests/
├── bin/
│   └── pandemic-iam           # Executable script
├── infection.yaml             # Infection definition
└── config.example.yaml       # Configuration template
```

#### Configuration Format
```yaml
# IMDSv2 metadata server configuration
metadata_server:
  host: 169.254.169.254  # Standard IMDS address
  port: 80               # Standard HTTP port

providers:
  aws:
    enabled: true
    region: us-east-1
    rolesanywhere_endpoint: https://rolesanywhere.us-east-1.amazonaws.com
    trust_anchor_arn: arn:aws:rolesanywhere:us-east-1:123:trust-anchor/ta-123
    profile_arn: arn:aws:rolesanywhere:us-east-1:123:profile/profile-123
    role_arn: arn:aws:iam::123456789012:role/PandemicRole

certificates:
  base_path: /etc/pandemic/certs
  default_cert: /etc/pandemic/certs/pandemic-iam.pem
  default_key: /etc/pandemic/certs/pandemic-iam.key
  file_permissions: 0600

security:
  max_session_duration: 43200    # 12 hours max token TTL
  credential_cache_ttl: 300      # 5 minutes credential cache
  token_cleanup_interval: 300    # 5 minutes token cleanup
  audit_all_operations: true
```

## Examples

### Installation and Setup
```bash
# 1. Install pandemic-iam as infection
pandemic-cli install github://pandemic-org/pandemic-iam --name iam-service

# 2. Configure certificates and providers
sudo cp /opt/pandemic/infections/pandemic-iam/config.example.yaml /etc/pandemic/iam/config.yaml

# 3. Generate certificates (or use existing CA)
sudo openssl req -x509 -newkey rsa:4096 -keyout /etc/pandemic/certs/pandemic-iam.key \
  -out /etc/pandemic/certs/pandemic-iam.crt -days 365 -nodes

# 4. Set secure permissions
sudo chown -R pandemic-iam:pandemic /etc/pandemic/iam/
sudo chmod 600 /etc/pandemic/certs/pandemic-iam.*

# 5. Start the metadata service
pandemic-cli start iam-service
```

### Application Usage (Zero Configuration)
```bash
# AWS CLI automatically discovers credentials
aws s3 ls

# Terraform uses IMDS automatically
terraform plan

# Python boto3 discovers credentials
python3 -c "import boto3; print(boto3.client('s3').list_buckets())"

# Manual IMDS access
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-pandemic-token-ttl-seconds: 3600")
curl -H "X-pandemic-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/aws
```

### Python Application Example
```python
import boto3

# No configuration needed - boto3 automatically uses IMDS
s3 = boto3.client('s3')
buckets = s3.list_buckets()

# Or manual IMDS access
import requests

# Get session token
token_response = requests.put(
    "http://169.254.169.254/latest/api/token",
    headers={"X-pandemic-token-ttl-seconds": "3600"}
)
token = token_response.text

# Get AWS credentials
creds_response = requests.get(
    "http://169.254.169.254/latest/meta-data/iam/security-credentials/aws",
    headers={"X-pandemic-token": token}
)
credentials = creds_response.json()

# Use credentials manually
s3 = boto3.client(
    's3',
    aws_access_key_id=credentials['AccessKeyId'],
    aws_secret_access_key=credentials['SecretAccessKey'],
    aws_session_token=credentials['Token']
)
```

### Multi-Cloud Support
```bash
# List available providers
TOKEN=$(curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-pandemic-token-ttl-seconds: 3600")
curl -H "X-pandemic-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/

# Get AWS credentials
curl -H "X-pandemic-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/aws

# Get Azure credentials (when implemented)
curl -H "X-pandemic-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/security-credentials/azure
```

## Testing

### Test Scenarios
- [x] IMDSv2 token generation and validation
- [x] Multi-provider credential retrieval
- [x] Automatic credential refresh and caching
- [x] Token expiration and cleanup
- [x] Certificate validation and security
- [x] Concurrent request handling
- [x] Error conditions and recovery
- [x] AWS SDK compatibility

### Integration Testing
- [x] AWS CLI credential discovery
- [x] Boto3 automatic credential chain
- [x] Terraform IMDS integration
- [x] Certificate-based authentication
- [x] Request signing validation

## Security Considerations

### IMDSv2 Security
- **Token-based access**: All requests require session token
- **Configurable TTL**: Token expiration from 1 second to 6 hours
- **IP-based access**: Only localhost can access metadata service
- **Request validation**: Proper headers and token format required

### Certificate Security
- **File permissions**: Certificates must have 600 or 400 permissions
- **Private key protection**: Keys never logged or transmitted
- **Certificate validation**: Expiration and usage checks
- **Trust anchor verification**: Certificate chain validation

### Credential Security
- **Temporary credentials**: No long-lived secrets stored
- **Automatic refresh**: Credentials refreshed before expiration
- **Secure caching**: In-memory credential cache with expiration
- **Audit logging**: All operations logged for security monitoring

### Network Security
- **Localhost only**: Service binds to 169.254.169.254 (link-local)
- **No external access**: Metadata service not accessible remotely
- **Request signing**: Cloud provider requests properly signed
- **TLS validation**: Certificate chain verification

## Deployment

### Systemd Integration
```ini
[Unit]
Description=Pandemic IAM Metadata Service
After=pandemic.service
Requires=pandemic.service

[Service]
Type=exec
User=pandemic-iam
Group=pandemic
ExecStart=/opt/pandemic/infections/pandemic-iam/bin/pandemic-iam
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Resource Requirements
- **Memory**: 256MB limit
- **CPU**: 25% quota
- **Network**: CAP_NET_BIND_SERVICE for port 80
- **Storage**: Minimal (configuration and certificates only)

### Monitoring
```bash
# Check service status
pandemic-cli status iam-service

# View logs
pandemic-cli logs iam-service

# Test metadata service
curl -X PUT "http://169.254.169.254/latest/api/token" -H "X-pandemic-token-ttl-seconds: 60"
```

## Migration

### From Manual Credential Management
1. Install pandemic-iam infection
2. Configure cloud provider settings and certificates
3. Start metadata service
4. Update applications to remove hardcoded credentials
5. Test automatic credential discovery
6. Monitor and validate operations

### Breaking Changes
- Applications must support IMDSv2 token-based access
- Requires CAP_NET_BIND_SERVICE capability for port 80
- Certificate-based cloud authentication setup required

### Rollback Plan
- Stop pandemic-iam infection
- Restore manual credential configuration in applications
- Remove certificate-based cloud provider setup
- Revert to previous authentication methods

## Implementation Status

### Completed Features
- [x] IMDSv2-compatible HTTP metadata server
- [x] Token-based security with configurable TTL
- [x] AWS IAM Roles Anywhere integration
- [x] Certificate-based request signing
- [x] Automatic credential caching and refresh
- [x] Configurable metadata server endpoint
- [x] Comprehensive audit logging
- [x] Systemd integration as infection
- [x] Multi-provider architecture

### Planned Features
- [ ] Azure Managed Identity support
- [ ] GCP Workload Identity Federation
- [ ] Certificate rotation automation
- [ ] Advanced security policies
- [ ] Prometheus metrics integration

## References

- [AWS Instance Metadata Service (IMDSv2)](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html)
- [AWS IAM Roles Anywhere](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/introduction.html)
- [Azure Managed Identity](https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/)
- [GCP Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [X.509 Certificate Standards](https://tools.ietf.org/html/rfc5280)