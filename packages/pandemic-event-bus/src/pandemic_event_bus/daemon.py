import os
from pathlib import Path
from typing import Any, Dict

from pandemic_common import UnixDaemonServer, route

from .events import Event, EventSocket, RateLimiter


class EventDaemon(UnixDaemonServer):
    """Event bus control plane daemon."""

    def __init__(
        self,
        socket_path: str = "/var/run/pandemic/event-bus.sock",
        events_dir: str = "/var/run/pandemic/events",
        rate_limit: int = 100,
        burst_size: int = 200,
        socket_mode: int = 660,
        socket_group: str = "pandemic",
        event_mode: int = 770,
    ):
        super().__init__(socket_path, socket_mode, socket_group=socket_group)
        self.events_dir = events_dir
        self.rate_limit = rate_limit
        self.burst_size = burst_size
        self.event_mode = event_mode
        self.sockets: Dict[str, EventSocket] = {}

    async def on_startup(self):
        """Initialize events directory and create core socket."""
        events_path = Path(self.events_dir)
        events_path.mkdir(parents=True, exist_ok=True)
        os.chmod(self.events_dir, int(str(self.event_mode), 8))

        await self._create_event_socket("core")
        self.logger.info("Event bus control plane started")

    async def on_shutdown(self):
        """Stop all event sockets."""
        stop_tasks = [socket.stop() for socket in self.sockets.values()]
        if stop_tasks:
            import asyncio

            await asyncio.gather(*stop_tasks, return_exceptions=True)
        self.sockets.clear()
        self.logger.info("Event bus control plane stopped")

    @route("publish")
    async def handle_publish(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Publish event to specified source."""
        source_id = payload.get("sourceId")
        event_type = payload.get("eventType")
        event_payload = payload.get("payload", {})

        if not source_id or not event_type:
            raise ValueError("sourceId and eventType are required")

        if source_id not in self.sockets:
            await self._create_event_socket(source_id)

        event = Event.create(source_id, event_type, event_payload)
        await self.sockets[source_id].publish(event)

        return {
            "eventId": event.eventId,
            "published": True,
            "sourceId": source_id,
            "subscriberCount": len(self.sockets[source_id].subscribers),
        }

    @route("createSource")
    async def handle_create_source(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create new event source socket."""
        source_id = payload.get("sourceId")

        if not source_id:
            raise ValueError("sourceId is required")

        if source_id in self.sockets:
            return {
                "sourceId": source_id,
                "socketPath": self.sockets[source_id].socket_path,
                "exists": True,
            }

        socket = await self._create_event_socket(source_id)
        return {"sourceId": source_id, "socketPath": socket.socket_path, "created": True}

    @route("getStats")
    async def handle_get_stats(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _create_event_socket(self, source_id: str) -> EventSocket:
        """Create a new event socket for the given source."""
        if source_id in self.sockets:
            return self.sockets[source_id]

        socket_path = os.path.join(self.events_dir, f"{source_id}.sock")

        rate_limiter = None
        if source_id != "core":
            rate_limiter = RateLimiter(self.rate_limit, self.burst_size)

        event_socket = EventSocket(
            socket_path, source_id, rate_limiter, self.socket_mode, self.socket_group
        )

        await event_socket.start()
        self.sockets[source_id] = event_socket
        self.logger.debug(f"Created event socket for {source_id}")

        return event_socket
