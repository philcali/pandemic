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
│   ├── pandemic-cli/        # CLI client package
│   ├── pandemic-iam/        # IMDSv2-style cloud metadata service
│   ├── pandemic-rest/       # HTTP REST API server
│   └── pandemic-console/    # Web-based dashboard interface
```

## Packages

### pandemic-common
Shared utilities, types, and protocol definitions used across all packages.

### pandemic-core  
Core daemon that manages infection lifecycle through Unix domain sockets and systemd integration.

### pandemic-cli
Command-line interface for interacting with the pandemic daemon. Includes bootstrap functionality for automated daemon setup.

### pandemic-iam
IMDSv2-style cloud metadata service that provides transparent host-wide access to cloud credentials via certificate-based authentication.

### pandemic-rest
HTTP REST API server infection that exposes pandemic-core functionality via RESTful endpoints with JWT authentication.

### pandemic-console
Web-based dashboard infection built with React + TypeScript that provides a modern UI for managing infections and monitoring system health.

## Quick Start

```bash
# Install development environment
make install-dev

# Run all tests
make test

# Bootstrap daemon (requires sudo)
sudo pandemic-cli bootstrap

# Use CLI
pandemic-cli status

# Install and start web interface (optional)
pandemic-cli install packages/pandemic-rest --name rest-api
pandemic-cli install packages/pandemic-console --name console
pandemic-cli start rest-api
pandemic-cli start console

# Access web dashboard at http://localhost:3000
```

## Bootstrap Command

The `bootstrap` command simplifies pandemic-core daemon installation by automating systemd service creation and system setup:

```bash
# Basic bootstrap (creates user, directories, systemd service)
sudo pandemic-cli bootstrap

# Preview actions without executing
sudo pandemic-cli bootstrap --dry-run

# Custom user and socket path
sudo pandemic-cli bootstrap --user myuser --socket-path /tmp/pandemic.sock

# Force reinstall existing service
sudo pandemic-cli bootstrap --force
```

The bootstrap process:
- Creates system user and required directories
- Generates systemd service file
- Enables and starts the pandemic-core service
- Validates successful daemon startup

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