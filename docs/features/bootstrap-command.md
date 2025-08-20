# Bootstrap Command

## Overview

The bootstrap command simplifies pandemic-core initial installation by automating systemd service creation, directory setup, and daemon configuration. This addresses the current challenge where users must manually configure systemd services, socket permissions, and system integration.

## Requirements

### Functional Requirements
- [ ] Create systemd service file for pandemic-core daemon
- [ ] Setup required directories with proper permissions
- [ ] Configure Unix domain socket permissions
- [ ] Enable and start the pandemic-core service
- [ ] Validate successful daemon startup
- [ ] Support dry-run mode for preview
- [ ] Handle existing installations (idempotent)

### Non-Functional Requirements
- [ ] Must run with appropriate privileges (sudo/root)
- [ ] Should complete within 30 seconds
- [ ] Must be idempotent (safe to run multiple times)
- [ ] Should provide clear error messages and rollback on failure

### Dependencies
- systemd (systemctl, journalctl)
- Unix-like operating system
- Python 3.8+ environment
- pandemic-core package installed

## Design

### Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ pandemic-cli│───▶│  Bootstrap  │───▶│   systemd   │
│   Command   │    │   Manager   │    │  Service    │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │                   ▼                   │
       │           ┌─────────────┐             │
       └──────────▶│ Validation  │◀────────────┘
                   │   & Setup   │
                   └─────────────┘
```

### API Changes

#### New CLI Command
```bash
pandemic-cli bootstrap [OPTIONS]
```

#### Options
- `--user USER`: System user for daemon (default: pandemic)
- `--socket-path PATH`: Unix socket path (default: /var/run/pandemic/daemon.sock)
- `--dry-run`: Preview actions without executing
- `--force`: Force reinstall existing service
- `--config PATH`: Custom daemon configuration file

### Implementation Details

#### Core Components
- **BootstrapManager**: Orchestrates the bootstrap process
- **SystemdServiceGenerator**: Creates systemd service files
- **PermissionManager**: Handles directory and socket permissions
- **ValidationManager**: Validates system requirements and installation

#### Service Template
```ini
[Unit]
Description=Pandemic Core Daemon
After=network.target
Wants=network.target

[Service]
Type=simple
User=pandemic
Group=pandemic
ExecStart=/usr/local/bin/pandemic-core
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Configuration
- Service file: `/etc/systemd/system/pandemic-core.service`
- Socket directory: `/var/run/pandemic/`
- State directory: `/var/lib/pandemic/`
- Log directory: `/var/log/pandemic/`

## Examples

### CLI Usage
```bash
# Basic bootstrap
pandemic-cli bootstrap

# Preview actions
pandemic-cli bootstrap --dry-run

# Custom user and socket path
pandemic-cli bootstrap --user myuser --socket-path /tmp/pandemic.sock

# Force reinstall
pandemic-cli bootstrap --force
```

### Expected Output
```
Bootstrapping pandemic-core daemon...
✓ Validating system requirements
✓ Creating system user 'pandemic'
✓ Setting up directories
✓ Generating systemd service
✓ Enabling pandemic-core.service
✓ Starting pandemic-core.service
✓ Validating daemon startup

Bootstrap completed successfully!
Daemon is running at /var/run/pandemic/daemon.sock
```

## Testing

### Test Scenarios
- [ ] Fresh installation on clean system
- [ ] Re-bootstrap existing installation
- [ ] Bootstrap with custom options
- [ ] Dry-run mode validation
- [ ] Error handling for insufficient permissions
- [ ] Rollback on partial failure

### Validation Criteria
- Service file created correctly
- Directories have proper permissions
- Daemon starts and responds to health check
- Socket accessible by intended users
- Service survives system reboot

## Migration

### Breaking Changes
None - this is a new feature.

### Migration Steps
1. Install updated pandemic-cli package
2. Run `pandemic-cli bootstrap` to setup daemon
3. Verify daemon functionality

### Rollback Plan
- Stop and disable service: `systemctl stop pandemic-core && systemctl disable pandemic-core`
- Remove service file: `rm /etc/systemd/system/pandemic-core.service`
- Remove directories: `rm -rf /var/run/pandemic /var/lib/pandemic /var/log/pandemic`
- Remove system user: `userdel pandemic`

## Implementation Plan

### Phase 1: Core Implementation
- [ ] Create BootstrapManager class
- [ ] Implement systemd service generation
- [ ] Add directory and permission setup
- [ ] Create CLI command interface

### Phase 2: Integration
- [ ] Add validation and error handling
- [ ] Implement dry-run mode
- [ ] Add rollback functionality
- [ ] Integration with existing CLI

### Phase 3: Testing & Documentation
- [ ] Unit tests for all components
- [ ] Integration tests on various systems
- [ ] Update CLI documentation
- [ ] Add troubleshooting guide

## References

- [systemd service documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Unix domain sockets](https://man7.org/linux/man-pages/man7/unix.7.html)
- [Python subprocess module](https://docs.python.org/3/library/subprocess.html)