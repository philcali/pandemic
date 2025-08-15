# Pandemic

A Python monorepo for edge computing infrastructure with systemd integration.

## Overview

Pandemic is a multi-package system for managing edge computing functions ("infections") on Unix-based systems. The system uses systemd for process management and Unix domain sockets for communication.

## Monorepo Structure

```
pandemic/
├── packages/
│   ├── pandemic-common/     # Shared types and utilities
│   ├── pandemic-core/       # Core daemon package  
│   └── pandemic-cli/        # CLI client package
```

## Packages

### pandemic-common
Shared utilities, types, and protocol definitions used across all packages.

### pandemic-core  
Core daemon that manages infection lifecycle through Unix domain sockets and systemd integration.

### pandemic-cli
Command-line interface for interacting with the pandemic daemon.

## Quick Start

```bash
# Install development environment
make install-dev

# Run all tests
make test

# Start daemon
pandemic

# Use CLI
pandemic-cli status
```

## Development

```bash
# Install packages in development mode
make install

# Run tests with coverage
make test-cov

# Format code
make format

# Lint code
make lint

# Run all quality checks
make quality

# Clean build artifacts
make clean
```

## Code Quality

The project uses Black, isort, and Flake8 for code formatting and linting:

- **Black**: Automatic code formatting (100 char line length)
- **isort**: Import sorting and organization  
- **Flake8**: Style guide enforcement and quality checks
- **MyPy**: Optional static type checking

See [LINTING.md](LINTING.md) for detailed configuration and usage.

## Documentation

Comprehensive documentation is available in the [docs/](docs/) directory:

- **[System Design](docs/DESIGN.md)** - Architecture and design decisions
- **[Requirements](docs/REQUIREMENTS.md)** - System requirements and specifications
- **[Installation Sources](docs/SOURCES.md)** - Source types and configuration
- **[Feature Designs](docs/features/)** - Detailed feature specifications