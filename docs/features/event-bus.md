# Event Bus System

## Overview

The Event Bus System enables asynchronous event communication between pandemic-core and infections through a distributed publish-subscribe architecture. This system allows infections to publish custom events and subscribe to events from other components, enabling real-time monitoring, inter-infection communication, audit logging, and reactive behaviors.

The event bus uses separate Unix domain sockets per infection to provide security isolation, filesystem-based access control, and scalable event distribution without multiplexing complexity.

## Requirements

### Functional Requirements
- [ ] Core daemon publishes system lifecycle events (infection start/stop/install/remove)
- [ ] Infections can publish custom events to their dedicated event streams
- [ ] Infections can subscribe to event streams from core and other infections
- [ ] Topic-based event filtering using pattern matching
- [ ] Event versioning with semantic versioning (default "1.0.0")
- [ ] Control-plane management of event subscriptions through existing control socket

### Non-Functional Requirements
- [ ] Best-effort delivery (no persistence or guaranteed delivery)
- [ ] Filesystem permissions for access control between infections
- [ ] Rate limiting to prevent event spam
- [ ] Minimal latency for real-time use cases
- [ ] Scalable to hundreds of concurrent infections

### Dependencies
- Unix domain sockets support
- Existing pandemic-core control socket infrastructure
- File system permissions for security isolation
- No backward compatibility requirements (net new feature)

## Design

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   pandemic-core │    │   infection-A   │    │   infection-B   │
│                 │    │                 │    │                 │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │ EventBus  │  │    │  │EventClient│  │    │  │EventClient│  │
│  │ Manager   │  │    │  │           │  │    │  │           │  │
│  └─────┬─────┘  │    │  └─────┬─────┘  │    │  └─────┬─────┘  │
└────────┼────────┘    └────────┼────────┘    └────────┼────────┘
         │                      │                      │
         ▼                      ▼                      ▼
/var/run/pandemic/events/       │                      │
├── core.sock ◄─────────────────┼──────────────────────┘
├── infection-A.sock ◄──────────┘
└── infection-B.sock
```

### Event Socket Structure

```
/var/run/pandemic/
├── control.sock              # Existing control channel
└── events/
    ├── core.sock            # Core daemon events (system-wide)
    ├── infection-abc123.sock # Per-infection event streams
    └── infection-xyz789.sock
```

### API Changes

#### Event Message Format
```json
{
  "eventId": "550e8400-e29b-41d4-a716-446655440000",
  "version": "1.0.0",
  "source": "core|infection-abc123",
  "type": "infection.started|custom.metric|system.alert",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "payload": {
    "infectionId": "infection-abc123",
    "customData": "..."
  }
}
```

#### Control Socket Commands

**Subscribe to Events**
```json
{
  "command": "subscribeEvents",
  "payload": {
    "infectionId": "infection-abc123",
    "subscriptions": [
      {"source": "core", "pattern": "infection.*"},
      {"source": "infection-xyz789", "pattern": "custom.*"}
    ]
  }
}
```

**Unsubscribe from Events**
```json
{
  "command": "unsubscribeEvents", 
  "payload": {
    "infectionId": "infection-abc123",
    "subscriptions": [
      {"source": "core", "pattern": "infection.*"}
    ]
  }
}
```

### Implementation Details

#### Core Components

**EventBus Manager (pandemic-core)**
- Manages event socket creation and cleanup
- Handles subscription routing and permissions
- Implements rate limiting per connection
- Publishes core system events

**EventClient (pandemic-common)**
- Provides simple publish/subscribe interface for infections
- Manages socket connections to event streams
- Handles event serialization/deserialization
- Implements topic pattern matching

**Event Router (pandemic-core)**
- Routes events between publishers and subscribers
- Enforces subscription permissions
- Applies rate limiting policies

#### Event Types

**Core System Events**
- `infection.installing` - Infection installation started
- `infection.installed` - Infection installation completed
- `infection.started` - Infection service started
- `infection.stopped` - Infection service stopped
- `infection.failed` - Infection operation failed
- `system.health` - System health status changes

**Custom Infection Events**
- `custom.*` - Application-specific events
- `metric.*` - Performance and monitoring metrics
- `alert.*` - Alert and notification events
- `audit.*` - Security and audit events

#### Configuration
```yaml
eventBus:
  enabled: true
  eventsDir: "/var/run/pandemic/events"
  rateLimit:
    maxEventsPerSecond: 100
    burstSize: 200
  permissions:
    defaultMode: "0660"
    group: "pandemic"
```

## Examples

### CLI Usage
```bash
# Subscribe to core events (via infection configuration)
pandemic-cli configure infection-abc123 --event-subscriptions "core:infection.*"

# View event subscriptions
pandemic-cli status infection-abc123 --show-events
```

### API Usage
```python
# Publishing events from an infection
from pandemic_common import EventClient

client = EventClient(infection_id="infection-abc123")
await client.publish("custom.metric", {
    "cpu_usage": 85.2,
    "memory_usage": 1024
})

# Subscribing to events
async def handle_infection_events(event):
    print(f"Infection {event.payload['infectionId']} changed state")

await client.subscribe("core", "infection.*", handle_infection_events)
```

## Testing

### Test Scenarios
- [ ] Core daemon publishes system events correctly
- [ ] Infections can publish and receive custom events
- [ ] Topic pattern matching works correctly
- [ ] Rate limiting prevents event spam
- [ ] Filesystem permissions isolate infection access
- [ ] Socket cleanup on infection removal
- [ ] Multiple subscribers receive same events
- [ ] Cross-infection communication works

### Validation Criteria
- Events delivered within 10ms for local sockets
- Rate limiting triggers at configured thresholds
- No memory leaks with long-running subscriptions
- Proper socket cleanup on process termination

## Migration

### Breaking Changes
- None (net new feature with no backward compatibility requirements)

### Migration Steps
1. Infections opt-in by using EventClient from pandemic-common
2. Configure event subscriptions via control socket
3. No changes required for existing infections

### Rollback Plan
- Disable event bus in configuration
- Remove event socket directory
- Infections gracefully handle missing event functionality

## Implementation Plan

### Phase 1: Core Infrastructure
- [ ] EventBus manager in pandemic-core
- [ ] Event socket creation and management
- [ ] Basic publish/subscribe functionality
- [ ] Event message format and serialization

### Phase 2: Client Integration
- [ ] EventClient in pandemic-common
- [ ] Control socket commands for subscription management
- [ ] Topic pattern matching
- [ ] Rate limiting implementation

### Phase 3: System Integration
- [ ] Core daemon event publishing
- [ ] Filesystem permissions and security
- [ ] Configuration management
- [ ] Error handling and cleanup

### Phase 4: Testing & Documentation
- [ ] Comprehensive test suite
- [ ] Performance benchmarking
- [ ] API documentation
- [ ] Usage examples and tutorials

## References

- [System Design](../DESIGN.md) - Overall pandemic architecture
- [Unix Domain Sockets](https://man7.org/linux/man-pages/man7/unix.7.html) - Transport mechanism
- [Publish-Subscribe Pattern](https://en.wikipedia.org/wiki/Publish%E2%80%93subscribe_pattern) - Design pattern reference