# Pandemic CLI

Command-line interface for Pandemic edge computing system administration.

## Overview

The pandemic-cli package provides a rich command-line interface for managing infections on the Pandemic daemon. It communicates with the daemon via Unix domain sockets and provides an intuitive interface for system administrators.

## Features

- **Rich Terminal UI** - Colorized output with tables and status indicators
- **Async Communication** - Non-blocking communication with daemon
- **Comprehensive Commands** - Full infection lifecycle management
- **Error Handling** - Clear error messages and connection handling
- **Flexible Configuration** - Custom socket paths and options

## Installation

```bash
# Install from source
pip install -e packages/pandemic-cli

# Or install with test dependencies
pip install -e "packages/pandemic-cli[test]"
```

## Usage

### Basic Commands

```bash
# Check daemon health
pandemic-cli health

# List all infections
pandemic-cli list

# List only running infections
pandemic-cli list --state running

# Get daemon status
pandemic-cli status

# Get specific infection status
pandemic-cli status <infection-id>
```

### Infection Management

```bash
# Install infection from GitHub
pandemic-cli install github://user/repo@v1.0.0

# Install with custom name
pandemic-cli install github://user/repo@v1.0.0 --name my-infection

# Remove infection
pandemic-cli remove <infection-id>

# Remove but keep files
pandemic-cli remove <infection-id> --keep-files
```

### Infection Control

```bash
# Start infection
pandemic-cli start <infection-id>

# Stop infection
pandemic-cli stop <infection-id>

# View logs
pandemic-cli logs <infection-id>

# View last 50 log lines
pandemic-cli logs <infection-id> --lines 50
```

### Configuration

```bash
# Use custom socket path
pandemic-cli --socket /tmp/pandemic.sock health

# All commands support custom socket
pandemic-cli --socket /custom/path list
```

## Command Reference

### Global Options

- `--socket PATH` - Path to pandemic daemon socket (default: `/var/run/pandemic.sock`)
- `--help` - Show help message

### Commands

#### `health`
Check if the pandemic daemon is running and healthy.

#### `list [--state STATE]`
List all infections with their status. Optional state filter.

#### `status [INFECTION_ID]`
Show daemon status (no ID) or specific infection status.

#### `install SOURCE [--name NAME]`
Install infection from source (GitHub, HTTP, or local path).

#### `remove INFECTION_ID [--keep-files]`
Remove infection. Use `--keep-files` to preserve installation files.

#### `start INFECTION_ID`
Start a stopped infection.

#### `stop INFECTION_ID`
Stop a running infection.

#### `logs INFECTION_ID [--lines N]`
Show infection logs. Default 100 lines.

## Examples

### Daily Administration

```bash
# Morning health check
pandemic-cli health
pandemic-cli status

# Check what's running
pandemic-cli list --state running

# Install new infection
pandemic-cli install github://pandemic-org/motion-detector@v2.1.0

# Check logs for issues
pandemic-cli logs motion-detector-abc123 --lines 200

# Restart problematic infection
pandemic-cli stop motion-detector-abc123
pandemic-cli start motion-detector-abc123
```

### Troubleshooting

```bash
# Check daemon connectivity
pandemic-cli health

# List all infections and their states
pandemic-cli list

# Get detailed status
pandemic-cli status <infection-id>

# Check recent logs
pandemic-cli logs <infection-id> --lines 500
```

## Output Format

The CLI uses rich formatting for better readability:

- ✅ **Green** - Success messages
- ❌ **Red** - Error messages  
- 🔵 **Blue** - Info messages
- **Tables** - Structured data display
- **Color-coded states** - Running (green), stopped (yellow), failed (red)

## Development

```bash
# Run tests
cd packages/pandemic-cli
pytest

# Format code
black src/ tests/

# Lint code
flake8 src/ tests/
```

## Error Handling

The CLI handles common error scenarios:

- **Connection failures** - Clear message when daemon is unreachable
- **Invalid commands** - Helpful error messages and suggestions
- **Missing infections** - Informative messages for non-existent IDs
- **Permission errors** - Clear indication of access issues

## Integration

The CLI is designed for:

- **Interactive use** - Rich terminal interface
- **Scripting** - Clean exit codes and parseable output
- **Automation** - Consistent command structure
- **Monitoring** - Status and health checking