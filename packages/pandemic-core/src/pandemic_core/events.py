"""Event bus system for pandemic daemon."""

import asyncio
import grp
import json
import logging
import os
import pwd
import time
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from weakref import WeakSet


@dataclass
class Event:
    """Event message structure."""

    eventId: str
    version: str
    source: str
    type: str
    timestamp: str
    payload: Dict[str, Any]

    @classmethod
    def create(
        cls, source: str, event_type: str, payload: Dict[str, Any], version: str = "1.0.0"
    ) -> "Event":
        """Create a new event with generated ID and timestamp."""
        return cls(
            eventId=str(uuid.uuid4()),
            version=version,
            source=source,
            type=event_type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            payload=payload,
        )

    def to_json(self) -> str:
        """Serialize event to JSON."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "Event":
        """Deserialize event from JSON."""
        return cls(**json.loads(data))


class RateLimiter:
    """Token bucket rate limiter for event publishing."""

    def __init__(self, max_events_per_second: int, burst_size: int):
        self.max_events_per_second = max_events_per_second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_refill = time.time()

    def allow_event(self) -> bool:
        """Check if an event is allowed under rate limit."""
        now = time.time()

        # Refill tokens based on time elapsed
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.max_events_per_second
        self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
        self.last_refill = now

        # Check if we have tokens available
        if self.tokens >= 1:
            self.tokens -= 1
            return True

        return False


class EventSocket:
    """Manages a single event socket for publishing/subscribing."""

    def __init__(
        self,
        socket_path: str,
        source_id: str,
        rate_limiter: Optional[RateLimiter] = None,
        socket_mode: int = 0o660,
        socket_group: str = "pandemic",
    ):
        self.socket_path = socket_path
        self.source_id = source_id
        self.rate_limiter = rate_limiter
        self.socket_mode = socket_mode
        self.socket_group = socket_group
        self.server: Optional[asyncio.Server] = None
        self.subscribers: WeakSet = WeakSet()
        self.logger = logging.getLogger(f"{__name__}.{source_id}")

    async def start(self):
        """Start the event socket server."""
        socket_path = Path(self.socket_path)
        socket_path.parent.mkdir(parents=True, exist_ok=True)

        if socket_path.exists():
            socket_path.unlink()

        try:
            self.server = await asyncio.start_unix_server(
                self._handle_subscriber, path=str(socket_path)
            )

            # Set socket permissions and group
            self._set_socket_permissions()

            self.logger.debug(f"Event socket started: {socket_path}")

        except Exception as e:
            self.logger.error(f"Failed to start event socket {self.source_id}: {e}")
            raise

    def _set_socket_permissions(self):
        """Set socket file permissions and group ownership."""
        try:
            # Set file mode
            os.chmod(self.socket_path, self.socket_mode)

            # Set group ownership if group exists
            try:
                group_info = grp.getgrnam(self.socket_group)
                os.chown(self.socket_path, -1, group_info.gr_gid)
            except KeyError:
                self.logger.warning(
                    f"Group '{self.socket_group}' not found, using default ownership"
                )
            except PermissionError:
                self.logger.warning(f"Cannot change group ownership of {self.socket_path}")

        except Exception as e:
            self.logger.error(f"Failed to set socket permissions: {e}")

    async def stop(self):
        """Stop the event socket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        socket_path = Path(self.socket_path)
        if socket_path.exists():
            try:
                socket_path.unlink()
            except Exception as e:
                self.logger.error(f"Failed to remove socket {self.socket_path}: {e}")

        self.logger.debug(f"Event socket stopped: {socket_path}")

    async def publish(self, event: Event):
        """Publish event to all subscribers."""
        # Apply rate limiting
        if self.rate_limiter and not self.rate_limiter.allow_event():
            self.logger.warning(
                f"Rate limit exceeded for {self.source_id}, dropping event {event.type}"
            )
            return

        if not self.subscribers:
            return

        try:
            event_data = event.to_json().encode("utf-8")
            event_length = len(event_data).to_bytes(4, "big")
            message = event_length + event_data

            # Send to all subscribers (best effort)
            disconnected = []
            for writer in list(self.subscribers):
                try:
                    writer.write(message)
                    await writer.drain()
                except Exception as e:
                    self.logger.debug(f"Failed to send event to subscriber: {e}")
                    disconnected.append(writer)

            # Clean up disconnected subscribers
            for writer in disconnected:
                self.subscribers.discard(writer)

        except Exception as e:
            self.logger.error(f"Error publishing event {event.type}: {e}")

    async def _handle_subscriber(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle new subscriber connection."""
        self.subscribers.add(writer)
        self.logger.debug(f"New subscriber connected to {self.source_id}")

        try:
            # Keep connection alive until client disconnects
            while True:
                data = await reader.read(1024)
                if not data:
                    break
        except Exception as e:
            self.logger.debug(f"Subscriber error: {e}")
        finally:
            self.subscribers.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                self.logger.warning(f"Error closing subscriber connection: {e}")
            self.logger.debug(f"Subscriber disconnected from {self.source_id}")


class EventBusManager:
    """Manages event sockets and routing for the pandemic daemon."""

    def __init__(
        self,
        events_dir: str = "/var/run/pandemic/events",
        rate_limit: int = 100,
        burst_size: int = 200,
        socket_mode: int = 0o660,
        socket_group: str = "pandemic",
    ):
        self.events_dir = events_dir
        self.rate_limit = rate_limit
        self.burst_size = burst_size
        self.socket_mode = socket_mode
        self.socket_group = socket_group
        self.sockets: Dict[str, EventSocket] = {}
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the event bus manager."""
        self.logger.info("Starting event bus manager")

        # Ensure events directory exists with proper permissions
        try:
            events_path = Path(self.events_dir)
            events_path.mkdir(parents=True, exist_ok=True)

            # Set directory permissions
            os.chmod(self.events_dir, 0o700)

            # Set directory group ownership
            try:
                group_info = grp.getgrnam(self.socket_group)
                os.chown(self.events_dir, -1, group_info.gr_gid)
            except (KeyError, PermissionError) as e:
                self.logger.warning(f"Cannot set directory group ownership: {e}")

        except Exception as e:
            self.logger.error(f"Failed to create events directory: {e}")
            raise

        # Create core event socket
        await self.create_event_socket("core")

    async def stop(self):
        """Stop the event bus manager."""
        self.logger.info("Stopping event bus manager")

        # Stop all event sockets
        stop_tasks = [socket.stop() for socket in self.sockets.values()]
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        self.sockets.clear()

    async def create_event_socket(self, source_id: str) -> EventSocket:
        """Create a new event socket for the given source."""
        if source_id in self.sockets:
            return self.sockets[source_id]

        socket_path = os.path.join(self.events_dir, f"{source_id}.sock")

        # Create rate limiter for non-core sources
        rate_limiter = None
        if source_id != "core":
            rate_limiter = RateLimiter(self.rate_limit, self.burst_size)

        event_socket = EventSocket(
            socket_path, source_id, rate_limiter, self.socket_mode, self.socket_group
        )

        try:
            await event_socket.start()
            self.sockets[source_id] = event_socket
            self.logger.debug(f"Created event socket for {source_id}")
            return event_socket

        except Exception as e:
            self.logger.error(f"Failed to create event socket for {source_id}: {e}")
            raise

    async def remove_event_socket(self, source_id: str):
        """Remove an event socket."""
        if source_id in self.sockets:
            try:
                await self.sockets[source_id].stop()
                del self.sockets[source_id]
                self.logger.debug(f"Removed event socket for {source_id}")
            except Exception as e:
                self.logger.error(f"Error removing event socket {source_id}: {e}")

    async def publish_event(self, source_id: str, event_type: str, payload: Dict[str, Any]):
        """Publish an event from the specified source."""
        if source_id not in self.sockets:
            self.logger.warning(f"No event socket for source: {source_id}")
            return

        try:
            event = Event.create(source_id, event_type, payload)
            await self.sockets[source_id].publish(event)
            self.logger.debug(f"Published event {event_type} from {source_id}")

        except Exception as e:
            self.logger.error(f"Failed to publish event {event_type} from {source_id}: {e}")

    def get_socket_path(self, source_id: str) -> Optional[str]:
        """Get the socket path for a source."""
        if source_id in self.sockets:
            return self.sockets[source_id].socket_path
        return None

    def list_sources(self) -> List[str]:
        """List all active event sources."""
        return list(self.sockets.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            "totalSources": len(self.sockets),
            "sources": {
                source_id: {
                    "subscriberCount": len(socket.subscribers),
                    "socketPath": socket.socket_path,
                }
                for source_id, socket in self.sockets.items()
            },
            "eventsDir": self.events_dir,
            "rateLimit": self.rate_limit,
            "burstSize": self.burst_size,
        }
