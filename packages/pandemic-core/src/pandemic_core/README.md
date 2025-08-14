# Pandemic Core Module

The core module implements the central pandemic daemon that manages infections via Unix domain sockets.

## Components

- **daemon.py** - Main daemon server with UDS handling
- **config.py** - Configuration management (YAML + environment)
- **handlers.py** - Message routing and operation handlers
- **state.py** - Persistent state management
- **__main__.py** - Entry point with signal handling

## Usage

```bash
# Run with default config
python -m pandemic.core

# Run with custom config
python -m pandemic.core /path/to/config.yaml
```

## API Operations

The daemon supports these operations via UDS:

- `health` - Health check
- `status` - Get daemon/infection status
- `list` - List infections
- `install` - Install new infection
- `remove` - Remove infection
- `start/stop/restart` - Control infections
- `getConfig/setConfig` - Configuration management
- `logs` - Retrieve logs
- `metrics` - Get metrics

## Configuration

See `example-daemon.yaml` for configuration options.

## Testing

Run the test with:
```bash
python3 test_core.py
```