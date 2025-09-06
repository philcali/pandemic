import asyncio
import grp
import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
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
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
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

        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.max_events_per_second
        self.tokens = min(self.burst_size, self.tokens + tokens_to_add)
        self.last_refill = now

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
        socket_mode: int = 660,
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

        self.server = await asyncio.start_unix_server(
            self._handle_subscriber, path=str(socket_path)
        )

        self._set_socket_permissions()
        self.logger.debug(f"Event socket started: {socket_path}")

    def _set_socket_permissions(self):
        """Set socket file permissions and group ownership."""
        try:
            os.chmod(self.socket_path, int(str(self.socket_mode), 8))

            try:
                group_info = grp.getgrnam(self.socket_group)
                os.chown(self.socket_path, -1, group_info.gr_gid)
            except (KeyError, PermissionError):
                self.logger.warning(f"Cannot set group ownership: {self.socket_group}")

        except Exception as e:
            self.logger.error(f"Failed to set socket permissions: {e}")

    async def stop(self):
        """Stop the event socket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        socket_path = Path(self.socket_path)
        if socket_path.exists():
            socket_path.unlink()

        self.logger.debug(f"Event socket stopped: {socket_path}")

    async def publish(self, event: Event):
        """Publish event to all subscribers."""
        if self.rate_limiter and not self.rate_limiter.allow_event():
            self.logger.warning(
                f"Rate limit exceeded for {self.source_id}, dropping event {event.type}"
            )
            return

        if not self.subscribers:
            self.logger.debug(f"No subscribers for {self.source_id}, dropping event {event.type}")
            return

        event_data = event.to_json().encode("utf-8")
        event_length = len(event_data).to_bytes(4, "big")
        message = event_length + event_data

        disconnected = []
        for writer in list(self.subscribers):
            try:
                writer.write(message)
                await writer.drain()
            except Exception as e:
                self.logger.debug(f"Failed to send event to subscriber: {e}")
                disconnected.append(writer)

        for writer in disconnected:
            self.subscribers.discard(writer)

    async def _handle_subscriber(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle new subscriber connection."""
        self.subscribers.add(writer)
        self.logger.debug(f"New subscriber connected to {self.source_id}")

        try:
            while not writer.is_closing():
                await asyncio.sleep(0.1)
        except Exception as e:
            self.logger.debug(f"Subscriber error: {e}")
        finally:
            self.subscribers.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as ie:
                self.logger.error(f"Error closing writer: {ie}")
                pass
            self.logger.debug(f"Subscriber disconnected from {self.source_id}")
