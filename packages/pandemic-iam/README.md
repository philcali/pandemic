# Pandemic IAM

Cloud provider IAM abstraction plugin for Pandemic edge computing system.

## Overview

Pandemic IAM provides secure, certificate-based authentication to cloud provider resources using mutual TLS (mTLS) certificates. It supports multiple cloud providers and exchanges X.509 certificates for temporary cloud credentials.

## Features

- **Certificate-based Authentication**: Uses X.509 certificates instead of long-lived API keys
- **Multiple Cloud Providers**: AWS IAM Roles Anywhere (Azure and GCP coming soon)
- **Unix File Permissions**: Simple security model using filesystem permissions
- **Temporary Credentials**: Automatic credential refresh and expiration handling
- **Unified API**: Consistent interface across all cloud providers

## Installation

```bash
# Install from source
pip install -e packages/pandemic-iam

# Or with test dependencies
pip install -e "packages/pandemic-iam[test]"
```

## Configuration

Pandemic IAM is configured through the main daemon configuration:

```yaml
# /etc/pandemic/daemon.yaml
iam:
  providers:
    aws:
      enabled: true
      region: us-east-1
      rolesanywhere_endpoint: https://rolesanywhere.us-east-1.amazonaws.com
      trust_anchor_arn: arn:aws:rolesanywhere:us-east-1:123456789012:trust-anchor/ta-123
      profile_arn: arn:aws:rolesanywhere:us-east-1:123456789012:profile/profile-123
      role_arn: arn:aws:iam::123456789012:role/PandemicRole

  certificates:
    base_path: /etc/pandemic/certs
    default_cert: /etc/pandemic/certs/pandemic.pem
    default_key: /etc/pandemic/certs/pandemic.key
    file_permissions: 0600
```

## Usage

### Python API

```python
from pandemic_iam import IAMManager

# Initialize manager
config = {
    "providers": {
        "aws": {
            "enabled": True,
            "region": "us-east-1",
            "trust_anchor_arn": "arn:aws:rolesanywhere:us-east-1:123:trust-anchor/ta-123",
            "profile_arn": "arn:aws:rolesanywhere:us-east-1:123:profile/profile-123",
            "role_arn": "arn:aws:iam::123456789012:role/PandemicRole"
        }
    }
}

manager = IAMManager(config)

# Get AWS credentials
credentials = await manager.get_credentials(
    provider="aws",
    certificate_path="/etc/pandemic/certs/infection.pem",
    private_key_path="/etc/pandemic/certs/infection.key",
    duration=3600
)

# Use with boto3
import boto3
s3 = boto3.client(
    's3',
    aws_access_key_id=credentials.access_key_id,
    aws_secret_access_key=credentials.secret_access_key,
    aws_session_token=credentials.session_token
)
```

### Certificate Setup

1. **Generate Certificate Authority (CA)**:
```bash
# Create CA private key
openssl genrsa -out ca.key 4096

# Create CA certificate
openssl req -new -x509 -days 365 -key ca.key -out ca.crt \
  -subj "/C=US/ST=CA/L=San Francisco/O=Pandemic/CN=Pandemic CA"
```

2. **Generate Client Certificate**:
```bash
# Create client private key
openssl genrsa -out client.key 2048

# Create certificate signing request
openssl req -new -key client.key -out client.csr \
  -subj "/C=US/ST=CA/L=San Francisco/O=Pandemic/CN=pandemic-client"

# Sign client certificate with CA
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out client.crt -days 365
```

3. **Set Secure Permissions**:
```bash
chmod 600 client.key client.crt
chown pandemic:pandemic client.key client.crt
```

### AWS IAM Roles Anywhere Setup

1. **Create Trust Anchor** in AWS Console or CLI
2. **Create Profile** with appropriate IAM roles
3. **Configure Certificate Authority** trust relationship
4. **Test Authentication** with pandemic-iam

## Security

### Certificate Security
- Certificates must have 600 or 400 file permissions
- Private keys are never logged or transmitted
- Certificate validation includes expiration and key usage checks
- Supports certificate revocation checking

### Credential Security
- Temporary credentials only (no long-lived secrets)
- Automatic credential refresh before expiration
- Secure credential caching with expiration
- Comprehensive audit logging

## Development

```bash
# Run tests
cd packages/pandemic-iam
pytest

# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Supported Providers

### AWS (Available)
- **IAM Roles Anywhere**: Certificate-based authentication
- **STS Integration**: Temporary credential generation
- **Regional Support**: All AWS regions
- **Role Assumption**: Multiple role support

### Azure (Coming Soon)
- **Managed Identity**: Certificate-based authentication
- **Service Principal**: Certificate authentication
- **Multi-tenant Support**: Cross-tenant authentication

### Google Cloud (Coming Soon)
- **Workload Identity**: Certificate-based authentication
- **Service Accounts**: Certificate authentication
- **Project Support**: Multi-project authentication

## Error Handling

Common errors and solutions:

### Certificate Validation Failed
```
Error: Certificate validation failed: expired certificate
```
- Check certificate expiration date
- Renew certificate if expired
- Verify certificate format (PEM)

### Insecure File Permissions
```
Error: Insecure private key permissions: /path/to/key.pem
```
- Set file permissions to 600: `chmod 600 /path/to/key.pem`
- Ensure proper ownership: `chown user:group /path/to/key.pem`

### AWS Authentication Failed
```
Error: AWS authentication failed: InvalidCertificate
```
- Verify trust anchor configuration in AWS
- Check certificate is signed by trusted CA
- Ensure profile has appropriate permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.