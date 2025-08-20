# Event Bus API Documentation

## Overview

The Pandemic Event Bus provides asynchronous event communication between the core daemon and infections through Unix domain sockets. This document describes the API for publishing and subscribing to events.

## Event Message Format

All events follow a standardized JSON format:

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

### Fields

- **eventId**: Unique UUID for the event
- **version**: Semantic version (default: "1.0.0")
- **source**: Event source identifier ("core" or infection ID)
- **type**: Dot-separated event type (e.g., "infection.started")
- **timestamp**: ISO 8601 timestamp in UTC
- **payload**: Event-specific data

## Core System Events

The core daemon publishes these system events:

### Infection Lifecycle Events

- `infection.installing` - Infection installation started
- `infection.installed` - Infection installation completed
- `infection.started` - Infection service started
- `infection.stopped` - Infection service stopped
- `infection.restarted` - Infection service restarted
- `infection.failed` - Infection operation failed
- `infection.removed` - Infection removed from system

### System Events

- `system.started` - Daemon started
- `system.stopping` - Daemon shutting down
- `system.subscription` - Event subscription changes

## Event Client API (Python)

### EventClient Class

```python
from pandemic_common import EventClient

# Initialize client
client = EventClient(infection_id="infection-abc123")

# Publish an event
await client.publish("custom.metric", {
    "cpu_usage": 85.2,
    "memory_usage": 1024
})

# Subscribe to events
async def handle_infection_events(event):
    print(f"Received: {event.type} from {event.source}")

await client.subscribe("core", "infection.*", handle_infection_events)

# Unsubscribe
await client.unsubscribe("core", "infection.*")

# Close client
await client.close()
```

### EventManager Class

High-level event management with automatic subscription registration:

```python
from pandemic_common import EventManager

# Initialize manager
manager = EventManager("infection-abc123")
await manager.initialize()

# Add subscription
async def handle_core_events(event):
    print(f"Core event: {event.type}")

await manager.add_subscription("core", "system.*", handle_core_events)

# Publish event
await manager.publish("custom.alert", {"level": "warning"})

# Close manager
await manager.close()
```

## Pattern Matching

Event subscriptions support glob-style patterns:

- `*` - Matches any single level (e.g., `infection.*` matches `infection.started`)
- `**` - Matches multiple levels (e.g., `custom.**` matches `custom.metric.cpu`)
- Exact match - `infection.started` matches only that event type

### Pattern Examples

```python
# Subscribe to all infection events
await client.subscribe("core", "infection.*", handler)

# Subscribe to all events from a source
await client.subscribe("core", "**", handler)

# Subscribe to specific metric events
await client.subscribe("infection-123", "metric.cpu.*", handler)

# Subscribe to all system health events
await client.subscribe("core", "system.health.**", handler)
```

## Control Socket Commands

### Subscribe to Events

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

**Response:**
```json
{
  "status": "success",
  "payload": {
    "status": "subscribed",
    "infectionId": "infection-abc123",
    "subscriptionCount": 2
  }
}
```

### Unsubscribe from Events

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

## CLI Usage

### View Event Bus Status

```bash
# Get daemon status including event bus info
pandemic-cli status

# Get configuration including event bus settings
pandemic-cli config
```

### Manage Event Subscriptions

```bash
# Subscribe infection to core events (via infection configuration)
pandemic-cli configure infection-abc123 --event-subscriptions "core:infection.*"

# View infection status including subscriptions
pandemic-cli status infection-abc123
```

## Configuration

### YAML Configuration

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

### Environment Variables

```bash
PANDEMIC_EVENT_BUS_ENABLED=true
PANDEMIC_EVENTS_DIR=/var/run/pandemic/events
PANDEMIC_EVENT_RATE_LIMIT=100
PANDEMIC_EVENT_BURST_SIZE=200
```

## Socket Structure

```
/var/run/pandemic/events/
├── core.sock              # Core daemon events
├── infection-abc123.sock  # Infection-specific events
└── infection-xyz789.sock
```

### Socket Permissions

- **Directory**: `0770` (owner/group read/write/execute)
- **Sockets**: `0660` (owner/group read/write)
- **Group**: `pandemic` (configurable)

## Rate Limiting

Rate limiting prevents event spam using a token bucket algorithm:

- **Default**: 100 events/second with burst of 200
- **Scope**: Per infection (core daemon exempt)
- **Behavior**: Events dropped when limit exceeded (logged)

## Error Handling

### Common Errors

- **Socket not found**: Event source doesn't exist
- **Permission denied**: Insufficient socket permissions
- **Rate limit exceeded**: Too many events published
- **Connection failed**: Network or socket issues

### Best Practices

1. **Handle connection failures gracefully**
2. **Implement exponential backoff for reconnection**
3. **Use appropriate event types and patterns**
4. **Monitor rate limiting logs**
5. **Clean up subscriptions on shutdown**

## Performance Characteristics

### Benchmarks

- **Throughput**: >1000 events/second publishing
- **Latency**: <10ms average delivery time
- **Scalability**: Supports hundreds of concurrent infections
- **Memory**: Minimal overhead per subscription

### Optimization Tips

1. **Use specific patterns** instead of wildcards when possible
2. **Batch event processing** in handlers
3. **Avoid blocking operations** in event handlers
4. **Monitor subscription counts** and clean up unused subscriptions

## Security Considerations

### Access Control

- Unix socket permissions control access
- Group membership required for event access
- No authentication beyond filesystem permissions

### Event Content

- Events are not encrypted (local Unix sockets)
- Avoid sensitive data in event payloads
- Consider payload size limits

## Examples

### Simple Event Publisher

```python
import asyncio
from pandemic_common import EventClient

async def publish_metrics():
    client = EventClient("metrics-collector")
    
    try:
        while True:
            # Collect metrics
            cpu_usage = get_cpu_usage()
            memory_usage = get_memory_usage()
            
            # Publish metric event
            await client.publish("metric.system", {
                "cpu": cpu_usage,
                "memory": memory_usage,
                "timestamp": time.time()
            })
            
            await asyncio.sleep(30)  # Every 30 seconds
            
    finally:
        await client.close()
```

### Event Subscriber

```python
import asyncio
from pandemic_common import EventManager

async def monitor_infections():
    manager = EventManager("infection-monitor")
    await manager.initialize()
    
    async def handle_infection_events(event):
        if event.type == "infection.failed":
            print(f"ALERT: Infection {event.payload['infectionId']} failed!")
        elif event.type == "infection.started":
            print(f"INFO: Infection {event.payload['infectionId']} started")
    
    # Subscribe to all infection lifecycle events
    await manager.add_subscription("core", "infection.*", handle_infection_events)
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await manager.close()
```

### Cross-Infection Communication

```python
# Infection A publishes data
await client_a.publish("data.processed", {
    "batch_id": "batch-123",
    "records": 1000,
    "status": "completed"
})

# Infection B subscribes to A's events
async def handle_data_events(event):
    if event.type == "data.processed":
        batch_id = event.payload["batch_id"]
        print(f"Processing batch {batch_id}")

await client_b.subscribe("infection-a", "data.*", handle_data_events)
```