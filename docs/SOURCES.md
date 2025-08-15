# Infection Sources

Pandemic supports multiple source types for installing infections. This document describes the supported source formats and their usage.

## Supported Source Types

### 🐙 GitHub Sources

Install infections directly from GitHub repositories.

**Format:** `github://user/repository@ref`

**Examples:**
```bash
# Install from main branch
pandemic-cli install github://pandemic-org/motion-detector

# Install specific version
pandemic-cli install github://pandemic-org/motion-detector@v2.1.0

# Install from branch
pandemic-cli install github://pandemic-org/motion-detector@develop
```

**Features:**
- Automatic archive download and extraction
- Version/branch/tag support via `@ref` syntax
- Supports public repositories
- Downloads as `.tar.gz` and extracts automatically

### 🌐 HTTP/HTTPS Sources

Install from any HTTP/HTTPS URL serving infection packages.

**Format:** `https://example.com/path/to/infection.tar.gz`

**Examples:**
```bash
# Install from archive
pandemic-cli install https://releases.example.com/infection-v1.0.0.tar.gz

# Install single file
pandemic-cli install https://raw.githubusercontent.com/user/repo/main/script.py
```

**Features:**
- Supports `.tar.gz` and `.tgz` archives (auto-extracted)
- Supports single file downloads
- Uses `curl` for reliable downloads
- Follows redirects automatically

### 📁 Local Sources

Install from local filesystem paths.

**Format:** `file:///path/to/source` or `/path/to/source`

**Examples:**
```bash
# Install from local directory
pandemic-cli install /home/user/my-infection

# Install from local archive
pandemic-cli install file:///tmp/infection.tar.gz

# Install single file
pandemic-cli install /path/to/script.py
```

**Features:**
- Supports directories (copies contents)
- Supports archives (extracts automatically)
- Supports single files
- Preserves file permissions

## Infection Configuration

Each infection should include an `infection.yaml` configuration file:

```yaml
metadata:
  name: my-infection
  version: 1.0.0
  description: Description of the infection
  author: Your Name

source:
  type: github
  url: github://user/repo@v1.0.0

systemd:
  user: pandemic-my-infection
  group: pandemic
  working_directory: /opt/pandemic/infections/my-infection
  environment:
    DEBUG: "false"
    LOG_LEVEL: "INFO"

execution:
  command: ./bin/my-infection
  restart: always
  restart_sec: 5

resources:
  memory_limit: 128M
  cpu_quota: 50%

security:
  capabilities: []
  read_only_root: true
  no_new_privileges: true
```

### Configuration Sections

#### `metadata`
- **name**: Infection name (used for systemd service)
- **version**: Version identifier
- **description**: Human-readable description
- **author**: Author information

#### `source`
- **type**: Source type (github, http, local)
- **url**: Original source URL

#### `systemd`
- **user**: System user to run as
- **group**: System group
- **working_directory**: Execution directory
- **environment**: Environment variables

#### `execution`
- **command**: Command to execute
- **restart**: Restart policy (always, on-failure, no)
- **restart_sec**: Seconds to wait before restart

#### `resources`
- **memory_limit**: Memory limit (e.g., "128M", "1G")
- **cpu_quota**: CPU quota percentage (e.g., "50%")

#### `security`
- **capabilities**: Linux capabilities to grant
- **read_only_root**: Make root filesystem read-only
- **no_new_privileges**: Prevent privilege escalation

## Security

### Source Validation

Configure allowed sources in daemon configuration:

```yaml
security:
  validate_signatures: true
  allowed_sources:
    - "github://trusted-org/"
    - "https://trusted.example.com/"
    - "file:///opt/trusted/"
```

### Installation Security

- Infections run as dedicated system users
- Resource limits enforced via systemd
- Security policies applied automatically
- Read-only root filesystem by default

## Installation Process

1. **Source Validation**: Check if source is allowed
2. **Download**: Fetch infection from source
3. **Extraction**: Extract archives if needed
4. **Configuration**: Load `infection.yaml`
5. **User Creation**: Create dedicated system user
6. **Systemd Service**: Generate systemd service file
7. **State Update**: Update daemon state

## Error Handling

Common installation errors:

### Source Not Found
```
Error: Source not found: github://user/nonexistent
```
- Verify repository exists and is accessible
- Check network connectivity

### Permission Denied
```
Error: Permission denied accessing /path/to/source
```
- Ensure daemon has read access to source
- Check file/directory permissions

### Invalid Configuration
```
Error: Invalid infection.yaml: missing required field 'execution.command'
```
- Verify `infection.yaml` syntax
- Ensure all required fields are present

### Security Violation
```
Error: Source not allowed: https://untrusted.com/infection
```
- Source not in `allowed_sources` list
- Contact administrator to whitelist source

## Best Practices

### Infection Development

1. **Include infection.yaml**: Always provide configuration
2. **Use relative paths**: Commands should be relative to working directory
3. **Handle signals**: Respond to SIGTERM for graceful shutdown
4. **Log to stdout/stderr**: Use standard output for logging
5. **Minimal dependencies**: Keep external dependencies minimal

### Source Management

1. **Version tags**: Use semantic versioning for releases
2. **Archive format**: Prefer `.tar.gz` for distribution
3. **Documentation**: Include README and usage instructions
4. **Testing**: Test installation on clean systems

### Security

1. **Principle of least privilege**: Request minimal capabilities
2. **Input validation**: Validate all external inputs
3. **Resource limits**: Set appropriate memory/CPU limits
4. **Read-only**: Use read-only root filesystem when possible

## Examples

See `examples/test-infection/` for a complete infection example with:
- Proper `infection.yaml` configuration
- Executable script in `bin/` directory
- Appropriate file permissions
- Documentation