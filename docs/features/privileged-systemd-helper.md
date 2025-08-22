# Privileged Systemd Helper

## Overview

A privileged helper service that manages systemd operations for pandemic infections while maintaining security isolation. This addresses the security issue where pandemic-core needs to write systemd service files to `/etc/systemd/system/` but should not run with root privileges.

## Requirements

### Functional Requirements
- [ ] Create systemd service files for infections in `/etc/systemd/system/`
- [ ] Manage systemd service lifecycle (start, stop, enable, disable)
- [ ] Validate all systemd operations for security
- [ ] Communicate via Unix domain socket with pandemic-core
- [ ] Log all privileged operations for audit trail
- [ ] Support service templates and drop-in configurations
- [ ] Handle service removal and cleanup

### Non-Functional Requirements
- [ ] Run as root with minimal attack surface
- [ ] Validate all inputs to prevent privilege escalation
- [ ] Rate limit requests to prevent abuse
- [ ] Fail securely on invalid requests
- [ ] Provide detailed error messages for debugging

### Dependencies
- systemd (systemctl, journalctl)
- Unix domain sockets
- Root privileges for systemd operations
- pandemic-core daemon as client

## Design

### Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ pandemic-   │───▶│ Privileged  │───▶│   systemd   │
│    core     │    │   Helper    │    │  Services   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │                   ▼                   │
       │           ┌─────────────┐             │
       └──────────▶│ Validation  │◀────────────┘
                   │ & Security  │
                   └─────────────┘
```

### API Changes

#### New Message Types
```json
{
  "command": "createService",
  "payload": {
    "serviceName": "pandemic-infection@myapp.service",
    "templateContent": "...",
    "overrideConfig": "...",
    "infectionId": "abc123"
  }
}
```

#### Response Format
```json
{
  "status": "success",
  "payload": {
    "serviceName": "pandemic-infection@myapp.service",
    "operation": "created"
  }
}
```

### Implementation Details

#### Core Components
- **HelperDaemon**: Main privileged service running as root
- **RequestValidator**: Validates and sanitizes all incoming requests
- **SystemdOperations**: Executes validated systemd commands
- **AuditLogger**: Logs all operations for security monitoring

#### Security Validation
- Service names must match `pandemic-infection@*.service` pattern
- File paths restricted to `/etc/systemd/system/pandemic-*`
- Template content validated against allowed patterns
- Rate limiting per client connection
- Input sanitization for all parameters

#### Configuration
```yaml
helper:
  socket_path: /var/run/pandemic/systemd-helper.sock
  socket_mode: 0660
  socket_group: pandemic
  max_requests_per_minute: 60
  allowed_service_patterns:
    - "pandemic-infection@*.service"
  allowed_paths:
    - "/etc/systemd/system/pandemic-*"
```

## Examples

### Service Creation
```python
# pandemic-core sends request
request = {
    "command": "createService",
    "payload": {
        "serviceName": "pandemic-infection@webapp.service",
        "templateContent": "[Unit]\nDescription=...",
        "overrideConfig": "[Service]\nEnvironment=...",
        "infectionId": "webapp-123"
    }
}
```

### Service Management
```python
# Start service
request = {
    "command": "startService",
    "payload": {
        "serviceName": "pandemic-infection@webapp.service"
    }
}

# Get status
request = {
    "command": "getStatus",
    "payload": {
        "serviceName": "pandemic-infection@webapp.service"
    }
}
```

## Testing

### Test Scenarios
- [ ] Valid service creation and management
- [ ] Invalid service name rejection
- [ ] Path traversal attack prevention
- [ ] Rate limiting enforcement
- [ ] Malformed request handling
- [ ] Service cleanup on removal
- [ ] Audit log generation

### Validation Criteria
- All systemd operations execute correctly
- Security validation blocks malicious requests
- Audit logs capture all operations
- Helper survives malformed inputs
- Performance meets rate limit requirements

## Migration

### Breaking Changes
- SystemdManager in pandemic-core will communicate via helper instead of direct systemctl
- Bootstrap process must create helper service
- New socket permissions and user setup required

### Migration Steps
1. Deploy privileged helper service
2. Update pandemic-core to use helper client
3. Modify bootstrap to setup helper service
4. Test systemd operations through helper
5. Remove direct systemctl calls from pandemic-core

### Rollback Plan
- Stop privileged helper service
- Revert pandemic-core to direct systemctl calls
- Add sudo rules for pandemic user as temporary fallback
- Remove helper service files

## Implementation Plan

### Phase 1: Core Helper Service
- [ ] Create HelperDaemon with socket server
- [ ] Implement RequestValidator with security checks
- [ ] Add SystemdOperations for service management
- [ ] Create basic audit logging

### Phase 2: Client Integration
- [ ] Create HelperClient for pandemic-core
- [ ] Update SystemdManager to use helper
- [ ] Add error handling and retry logic
- [ ] Implement rate limiting

### Phase 3: Bootstrap & Security
- [ ] Update bootstrap to create helper service
- [ ] Add comprehensive security validation
- [ ] Implement audit logging
- [ ] Add monitoring and alerting

## References

- [systemd service documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Unix domain socket security](https://man7.org/linux/man-pages/man7/unix.7.html)
- [Privilege separation patterns](https://en.wikipedia.org/wiki/Privilege_separation)