# Systemd Integration

The pandemic core module integrates with systemd to manage infection services.

## Architecture

- **Service Template**: `/etc/systemd/system/pandemic-infection@.service`
- **Drop-in Configs**: `/etc/systemd/system/pandemic-infection@{name}.service.d/pandemic.conf`
- **Service Names**: `pandemic-infection@{infection-name}.service`

## Service Template

The systemd service template is automatically created:

```ini
[Unit]
Description=Pandemic Infection: %i
After=pandemic.service
Requires=pandemic.service
PartOf=pandemic.service

[Service]
Type=simple
User=pandemic-%i
Group=pandemic
WorkingDirectory=/opt/pandemic/infections/%i
ExecStart=/opt/pandemic/infections/%i/bin/%i
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=pandemic.target
```

## Operations

### Install Infection
1. Creates systemd service template (if needed)
2. Creates drop-in directory for infection-specific config
3. Generates override configuration with environment and resources
4. Reloads systemd daemon

### Remove Infection
1. Stops and disables service
2. Removes drop-in configuration directory
3. Reloads systemd daemon

### Service Control
- `start` - Starts systemd service
- `stop` - Stops systemd service  
- `restart` - Restarts systemd service

### Status Monitoring
- Queries systemd service properties
- Maps systemd states to infection states
- Retrieves resource usage (memory, CPU)

### Log Access
- Uses `journalctl` to retrieve service logs
- Supports filtering by lines and time range
- Returns structured log entries

## Security

- Each infection runs as dedicated user: `pandemic-{infection-name}`
- All infections share `pandemic` group
- Resource limits enforced via systemd
- Working directory isolation

## Requirements

- systemd (Linux only)
- Root privileges for service management
- `pandemic` group must exist
- User accounts for infections must exist

## Example Usage

```python
from pandemic.core.systemd import SystemdManager

manager = SystemdManager(config)

# Create service
service_name = await manager.create_service(infection_id, infection_data)

# Control service
await manager.start_service(service_name)
await manager.stop_service(service_name)

# Get status
status = await manager.get_service_status(service_name)

# Get logs
logs = await manager.get_service_logs(service_name, lines=100)
```