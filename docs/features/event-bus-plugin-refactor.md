# Event Bus Plugin Refactor

## Overview

Refactor the event bus from a tightly-coupled core daemon feature to a standalone infection plugin. This change decouples the event bus from the core daemon, making it an optional, independently manageable service that follows the same patterns as other infections.

The current event bus is embedded within the core daemon, creating tight coupling and making it difficult to manage independently. By converting it to an infection plugin, we achieve better modularity, optional deployment, and consistent architecture patterns.

## Requirements

### Functional Requirements
- [ ] Event bus operates as standalone infection plugin
- [ ] Core daemon communicates with event bus via UDS protocol
- [ ] Event bus supports same publish/subscribe functionality
- [ ] Graceful degradation when event bus is unavailable
- [ ] Event bus can be installed/removed like any infection
- [ ] Existing event bus API compatibility maintained

### Non-Functional Requirements
- [ ] No performance degradation from UDS communication
- [ ] Event bus startup/shutdown independent of core daemon
- [ ] Memory usage reduced in core daemon when event bus not installed
- [ ] Event bus restartable without affecting core daemon

### Dependencies
- pandemic-common (UnixDaemonServer, routing)
- pandemic-core (for UDS client communication)
- systemd (for infection lifecycle management)

## Design

### Architecture

Current tightly-coupled architecture:
```
┌─────────────────────────────────────┐
│           Core Daemon               │
│  ┌─────────────────────────────┐    │
│  │      EventBusManager        │    │
│  │  ┌─────────┐ ┌─────────┐    │    │
│  │  │ Socket1 │ │ Socket2 │    │    │
│  │  └─────────┘ └─────────┘    │    │
│  └─────────────────────────────┘    │
│  ┌─────────────────────────────┐    │
│  │     Infection Management    │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

New decoupled architecture:
```
┌─────────────────────┐    UDS     ┌─────────────────────┐
│    Core Daemon      │◄──────────►│   Event Bus Plugin  │
│                     │  Protocol  │                     │
│ ┌─────────────────┐ │            │ ┌─────────────────┐ │
│ │ Infection Mgmt  │ │            │ │  EventDaemon    │ │
│ └─────────────────┘ │            │ │   (Routes)      │ │
│ ┌─────────────────┐ │            │ └─────────────────┘ │
│ │ Event Client    │ │            │ ┌─────────────────┐ │
│ │ (Optional)      │ │            │ │  EventSockets   │ │
│ └─────────────────┘ │            │ │ (Streaming)     │ │
└─────────────────────┘            │ └─────────────────┘ │
                                   └─────────────────────┘
```

### API Changes

#### Core Daemon Changes
- Remove embedded EventBusManager
- Add optional EventClient for UDS communication
- Graceful event publishing when event bus unavailable

#### Event Bus Plugin API
```json
{
  "command": "publish",
  "payload": {
    "sourceId": "core",
    "eventType": "infection.started",
    "payload": {"infectionId": "abc123"}
  }
}
```

#### Response Format
```json
{
  "status": "success",
  "payload": {
    "eventId": "uuid-here",
    "published": true,
    "subscriberCount": 3
  }
}
```

### Implementation Details

#### Core Components
- **EventDaemon**: UDS server with @route handlers for control plane
- **EventSocket**: Unchanged streaming sockets for data plane
- **EventClient**: UDS client in core daemon for publishing
- **Event Bus Package**: Standalone infection package

#### Configuration
Event bus gets its own infection configuration:
```yaml
metadata:
  name: pandemic-event-bus
  version: 1.0.0
  description: Event bus service for pandemic system

execution:
  command: ./bin/pandemic-event-daemon
  
systemd:
  user: pandemic-events
  
resources:
  memoryLimit: 128MB
```

## Examples

### Installation
```bash
# Install event bus as infection
pandemic-cli install pandemic-event-bus --name event-bus

# Start event bus
pandemic-cli start event-bus

# Core daemon automatically detects and uses event bus
```

### Core Daemon Integration
```python
# Core daemon publishes events via UDS client
async def _publish_event(self, event_type: str, payload: Dict[str, Any]):
    """Publish event via event daemon if available."""
    try:
        if not self.event_client:
            self.event_client = EventClient()
        await self.event_client.publish("core", event_type, payload)
    except ConnectionError:
        # Graceful degradation - event bus not available
        self.logger.debug("Event bus not available, skipping event")
```

## Testing

### Test Scenarios
- [ ] Core daemon operates without event bus installed
- [ ] Event bus installation and removal
- [ ] Event publishing with and without event bus
- [ ] Event bus restart while core daemon running
- [ ] Performance comparison with embedded event bus

### Validation Criteria
- Core daemon memory usage reduced when event bus not installed
- Event publishing latency within 5ms of embedded version
- Zero core daemon downtime during event bus lifecycle operations

## Migration

### Breaking Changes
- Event bus configuration moves from core daemon to infection config
- Event bus no longer starts automatically with core daemon
- Applications depending on event bus must ensure it's installed

### Migration Steps
1. Install event bus as infection: `pandemic-cli install pandemic-event-bus --name event-bus`
2. Update core daemon configuration to remove event bus settings
3. Restart core daemon to use new event client
4. Verify event publishing works via UDS communication

### Rollback Plan
- Revert core daemon to embedded event bus version
- Remove event bus infection
- Restore original core daemon configuration

## Implementation Plan

### Phase 1: Event Bus Plugin Creation
- [ ] Create pandemic-event-bus package structure
- [ ] Implement EventDaemon with @route handlers
- [ ] Create infection.yaml configuration
- [ ] Package as installable infection

### Phase 2: Core Daemon Refactoring
- [ ] Remove embedded EventBusManager from core daemon
- [ ] Implement EventClient for UDS communication
- [ ] Add graceful degradation for missing event bus
- [ ] Update configuration to remove event bus settings

### Phase 3: Testing & Documentation
- [ ] Integration testing with core daemon
- [ ] Performance benchmarking
- [ ] Update installation documentation
- [ ] Migration guide for existing deployments

## References

- [Event Bus API Documentation](event-bus-api.md)
- [Event Bus Examples](event-bus-examples.md)
- [UnixDaemonServer Architecture](../DESIGN.md#daemon-abstraction)