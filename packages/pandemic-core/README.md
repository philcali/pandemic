# Pandemic Core

Core daemon package for the Pandemic edge computing system.

## Overview

The pandemic-core package provides the central daemon that manages infection lifecycle through Unix domain sockets and systemd integration.

## Features

- **Unix Domain Socket Server** - Lightweight IPC for local communication
- **Systemd Integration** - Native Linux service management
- **Async Architecture** - Non-blocking operations with asyncio
- **Persistent State** - JSON-based state management
- **Resource Management** - Memory and CPU limits via systemd
- **Structured Logging** - JSON logging with journald integration

## Installation

```bash
# Install from source
pip install -e packages/pandemic-core

# Or install with test dependencies
pip install -e "packages/pandemic-core[test]"
```

## Usage

```bash
# Start daemon with default config
pandemic

# Start with custom config
pandemic /path/to/config.yaml
```

## Configuration

See `example-daemon.yaml` in the project root for configuration options.

## API

The daemon exposes these operations via Unix domain socket:

- `health` - Health check
- `install` - Install new infection
- `remove` - Remove infection
- `start/stop/restart` - Control infections
- `status` - Get infection status
- `list` - List all infections
- `logs` - Retrieve infection logs
- `metrics` - Get resource metrics

## Development

```bash
# Run tests
cd packages/pandemic-core
pytest

# Run with coverage
pytest --cov=src/pandemic_core
```