# Pandemic IAM - Cloud Provider Abstraction

## Overview

Pandemic IAM is a plugin system that provides secure, certificate-based authentication to cloud provider resources (AWS, Azure, Google Cloud). It uses mutual TLS (mTLS) certificates for authentication, similar to AWS IAM Anywhere, where the certificate is exchanged for temporary cloud credentials.

The plugin enables edge devices to securely access cloud resources using X.509 certificates stored with Unix file permissions, eliminating the need for long-lived API keys or secrets. The customer owns the cloud account and grants trust to the certificate authority.

## Requirements

### Functional Requirements
- [ ] mTLS certificate-based authentication to cloud providers
- [ ] Support multiple cloud providers (AWS, Azure, GCP)
- [ ] Exchange certificates for temporary cloud credentials (SigV4, etc.)
- [ ] Manage certificate storage with Unix file permissions
- [ ] Handle credential refresh and expiration automatically
- [ ] Provide unified API for credential exchange
- [ ] Support certificate rotation and renewal
- [ ] Audit all authentication exchanges

### Non-Functional Requirements
- [ ] Secure credential storage and transmission
- [ ] High availability with credential caching
- [ ] Low latency for credential operations (<100ms)
- [ ] Scalable to hundreds of concurrent infections
- [ ] Comprehensive audit trail
- [ ] Zero-trust security model

### Dependencies
- Cloud provider SDKs (boto3, azure-sdk, google-cloud)
- Secure credential storage (systemd-creds, HashiCorp Vault)
- Certificate management for mTLS
- Pandemic core daemon for plugin lifecycle

## Design

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Infection     │───▶│  Pandemic IAM   │───▶│ Cloud Provider  │
│   (Client)      │    │    Plugin       │    │  IAM Anywhere   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  mTLS Cert      │    │  Temp Creds     │
                       │  (Unix perms)   │    │  (SigV4/Bearer) │
                       └─────────────────┘    └─────────────────┘
```

### Core Components

#### Certificate Manager
- X.509 certificate loading and validation
- Unix file permission enforcement
- Certificate chain verification
- Certificate renewal handling

#### Cloud Provider Adapters
- AWS Adapter (IAM Anywhere, STS)
- Azure Adapter (Certificate-based auth)
- GCP Adapter (Certificate-based service accounts)

#### Credential Exchange
- mTLS handshake with cloud providers
- Certificate-to-credential exchange
- Temporary credential caching
- Automatic token refresh

#### Authentication Controller
- Certificate validation
- Trust anchor verification
- Authentication audit logging
- Certificate revocation checking

### API Changes

#### New Message Types

**Get Credentials**
```json
{
  "command": "iam.getCredentials",
  "payload": {
    "provider": "aws|azure|gcp",
    "certificatePath": "/etc/pandemic/certs/infection.pem",
    "keyPath": "/etc/pandemic/certs/infection.key",
    "trustAnchor": "pandemic-ca",
    "duration": 3600
  }
}
```

**List Providers**
```json
{
  "command": "iam.listProviders",
  "payload": {}
}
```

**Exchange Certificate**
```json
{
  "command": "iam.exchangeCertificate",
  "payload": {
    "provider": "aws",
    "certificatePath": "/etc/pandemic/certs/infection.pem",
    "keyPath": "/etc/pandemic/certs/infection.key",
    "trustAnchorArn": "arn:aws:rolesanywhere:us-east-1:123456789012:trust-anchor/ta-123",
    "profileArn": "arn:aws:rolesanywhere:us-east-1:123456789012:profile/profile-123"
  }
}
```

#### Response Formats

**Credentials Response**
```json
{
  "status": "success",
  "payload": {
    "provider": "aws",
    "credentials": {
      "accessKeyId": "AKIA...",
      "secretAccessKey": "...",
      "sessionToken": "...",
      "expiration": "2024-01-01T12:00:00Z"
    },
    "region": "us-east-1",
    "permissions": ["s3:GetObject", "s3:PutObject"]
  }
}
```

### Implementation Details

#### Plugin Structure
```
pandemic-iam/
├── src/
│   ├── pandemic_iam/
│   │   ├── __init__.py
│   │   ├── plugin.py          # Main plugin interface
│   │   ├── manager.py         # IAM manager
│   │   ├── providers/         # Cloud provider adapters
│   │   │   ├── __init__.py
│   │   │   ├── base.py        # Abstract provider
│   │   │   ├── aws.py         # AWS implementation
│   │   │   ├── azure.py       # Azure implementation
│   │   │   └── gcp.py         # GCP implementation
│   │   ├── credentials.py     # Credential management
│   │   ├── security.py        # Security policies
│   │   └── audit.py           # Audit logging
│   └── tests/
└── infection.yaml             # Plugin configuration
```

#### Configuration Format
```yaml
metadata:
  name: pandemic-iam
  version: 1.0.0
  description: Cloud provider IAM abstraction plugin
  author: Pandemic Team

plugin:
  type: iam
  interface_version: "1.0"

providers:
  aws:
    enabled: true
    region: us-east-1
    rolesanywhere_endpoint: https://rolesanywhere.us-east-1.amazonaws.com
    trust_anchor_arn: arn:aws:rolesanywhere:us-east-1:123456789012:trust-anchor/ta-123
    profile_arn: arn:aws:rolesanywhere:us-east-1:123456789012:profile/profile-123
    
  azure:
    enabled: false
    tenant_id: ${AZURE_TENANT_ID}
    certificate_auth_endpoint: https://login.microsoftonline.com
    
  gcp:
    enabled: false
    project_id: ${GCP_PROJECT_ID}
    certificate_auth_endpoint: https://oauth2.googleapis.com

security:
  max_session_duration: 3600
  credential_cache_ttl: 300
  audit_all_operations: true
  require_mfa: false

certificates:
  base_path: /etc/pandemic/certs
  ca_bundle: /etc/pandemic/certs/ca-bundle.pem
  default_cert: /etc/pandemic/certs/pandemic.pem
  default_key: /etc/pandemic/certs/pandemic.key
  file_permissions: 0600
  renewal_days: 30
```

## Examples

### CLI Usage
```bash
# List available providers
pandemic-cli iam list-providers

# Get AWS credentials using certificate
pandemic-cli iam get-credentials --provider aws --cert /etc/pandemic/certs/infection.pem

# Exchange certificate for temporary credentials
pandemic-cli iam exchange-certificate --provider aws --cert /etc/pandemic/certs/infection.pem
```

### Infection Usage
```python
# Python infection using IAM plugin
import boto3
from pandemic_iam import get_credentials

# Get temporary AWS credentials using certificate
creds = await get_credentials(
    provider="aws",
    certificate_path="/etc/pandemic/certs/infection.pem",
    key_path="/etc/pandemic/certs/infection.key"
)

# Use credentials with boto3
s3 = boto3.client(
    's3',
    aws_access_key_id=creds['accessKeyId'],
    aws_secret_access_key=creds['secretAccessKey'],
    aws_session_token=creds['sessionToken']
)

# Perform operations
response = s3.list_objects_v2(Bucket='my-bucket')
```

### UDS Protocol
```python
# Direct UDS communication
async def get_cloud_credentials():
    message = {
        "command": "iam.getCredentials",
        "payload": {
            "provider": "aws",
            "certificatePath": "/etc/pandemic/certs/infection.pem",
            "keyPath": "/etc/pandemic/certs/infection.key",
            "duration": 1800
        }
    }
    
    response = await client.send_message(message)
    return response["payload"]["credentials"]
```

## Testing

### Test Scenarios
- [ ] Multi-provider credential generation
- [ ] Token refresh and expiration handling
- [ ] RBAC policy enforcement
- [ ] Credential caching and performance
- [ ] Security policy violations
- [ ] Provider failover scenarios
- [ ] Audit log generation
- [ ] Concurrent access patterns

### Validation Criteria
- Credentials work with actual cloud APIs
- Token refresh occurs before expiration
- Unauthorized access is blocked
- All operations are audited
- Performance meets latency requirements
- Security policies are enforced

## Migration

### Breaking Changes
- New plugin type requires core daemon updates
- Additional dependencies for cloud SDKs
- New configuration format for IAM settings

### Migration Steps
1. Install pandemic-iam plugin
2. Configure cloud provider settings
3. Update infection configurations to use IAM
4. Test credential access and operations
5. Enable audit logging and monitoring

### Rollback Plan
- Disable IAM plugin in daemon configuration
- Revert to direct credential management in infections
- Remove cloud provider dependencies
- Restore previous authentication methods

## Implementation Plan

### Phase 1: Core Framework
- [ ] Plugin interface and manager
- [ ] Abstract provider base class
- [ ] Credential storage and caching
- [ ] Basic security policies
- [ ] UDS message handlers

### Phase 2: AWS Implementation
- [ ] AWS STS integration
- [ ] EC2 instance profile support
- [ ] IAM role assumption
- [ ] S3, EC2, Lambda permissions
- [ ] CloudWatch audit logging

### Phase 3: Multi-Provider Support
- [ ] Azure managed identity
- [ ] GCP service accounts
- [ ] Provider abstraction testing
- [ ] Cross-provider credential management
- [ ] Unified audit trail

### Phase 4: Advanced Features
- [ ] MFA support
- [ ] Just-in-time access
- [ ] Resource-based policies
- [ ] Credential rotation automation
- [ ] Threat detection integration

## Security Considerations

### Credential Protection
- Never log credentials in plaintext
- Use secure storage backends (systemd-creds, Vault)
- Encrypt credentials at rest and in transit
- Implement credential shredding after use

### Access Control
- Enforce least-privilege principle
- Validate resource access patterns
- Implement time-based access controls
- Support emergency access revocation

### Audit Requirements
- Log all credential requests and usage
- Track resource access patterns
- Monitor for suspicious activities
- Integrate with SIEM systems

## References

- AWS STS Documentation
- Azure Managed Identity Guide
- GCP Workload Identity Federation
- NIST Cybersecurity Framework
- Zero Trust Architecture Principles