"""Event client for pandemic infections."""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class EventSubscription:
    """Event subscription configuration."""

    source: str
    pattern: str


class EventClient:
    """Client for publishing and subscribing to pandemic events."""

    def __init__(self, infection_id: str, events_dir: str = "/var/run/pandemic/events"):
        self.infection_id = infection_id
        self.events_dir = events_dir
        self.subscriptions: Dict[str, asyncio.Task] = {}
        self.logger = logging.getLogger(f"{__name__}.{infection_id}")

    async def publish(self, event_type: str, payload: Dict[str, Any], version: str = "1.0.0"):
        """Publish an event to this infection's event stream."""
        from pandemic_core.events import Event

        socket_path = f"{self.events_dir}/{self.infection_id}.sock"

        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)

            # Create and serialize event
            event = Event.create(self.infection_id, event_type, payload, version)
            event_data = event.to_json().encode("utf-8")
            event_length = len(event_data).to_bytes(4, "big")

            # Send event (infections publish by connecting and sending)
            writer.write(event_length + event_data)
            await writer.drain()

            writer.close()
            await writer.wait_closed()

            self.logger.debug(f"Published event {event_type}")

        except Exception as e:
            self.logger.error(f"Failed to publish event {event_type}: {e}")
            raise

    async def subscribe(self, source: str, pattern: str, handler: Callable):
        """Subscribe to events from a source with pattern matching."""
        subscription_key = f"{source}:{pattern}"

        if subscription_key in self.subscriptions:
            self.logger.warning(f"Already subscribed to {subscription_key}")
            return

        # Start subscription task
        task = asyncio.create_task(self._subscription_loop(source, pattern, handler))
        self.subscriptions[subscription_key] = task

        self.logger.debug(f"Subscribed to {subscription_key}")

    async def unsubscribe(self, source: str, pattern: str):
        """Unsubscribe from events."""
        subscription_key = f"{source}:{pattern}"

        if subscription_key in self.subscriptions:
            self.subscriptions[subscription_key].cancel()
            del self.subscriptions[subscription_key]
            self.logger.debug(f"Unsubscribed from {subscription_key}")

    async def close(self):
        """Close all subscriptions."""
        for task in self.subscriptions.values():
            task.cancel()

        # Wait for tasks to complete
        if self.subscriptions:
            await asyncio.gather(*self.subscriptions.values(), return_exceptions=True)

        self.subscriptions.clear()
        self.logger.debug("Closed all subscriptions")

    async def _subscription_loop(self, source: str, pattern: str, handler: Callable):
        """Main subscription loop for receiving events."""
        socket_path = f"{self.events_dir}/{source}.sock"
        pattern_regex = self._compile_pattern(pattern)

        while True:
            try:
                reader, writer = await asyncio.open_unix_connection(socket_path)
                self.logger.debug(f"Connected to {source} event stream")

                try:
                    while True:
                        # Read event length
                        length_data = await reader.readexactly(4)
                        if not length_data:
                            break

                        event_length = int.from_bytes(length_data, "big")

                        # Read event data
                        event_data = await reader.readexactly(event_length)
                        event_json = event_data.decode("utf-8")

                        # Parse event
                        from pandemic_core.events import Event

                        event = Event.from_json(event_json)

                        # Check if event matches pattern
                        if pattern_regex.match(event.type):
                            try:
                                await handler(event)
                            except Exception as e:
                                self.logger.error(f"Error in event handler: {e}")

                except asyncio.IncompleteReadError:
                    self.logger.debug(f"Connection to {source} closed")
                finally:
                    writer.close()
                    await writer.wait_closed()

                # Reconnect after delay
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in subscription loop for {source}: {e}")
                await asyncio.sleep(5)  # Longer delay on error

    def _compile_pattern(self, pattern: str) -> re.Pattern:
        """Compile glob-style pattern to regex."""
        # Convert glob pattern to regex
        # * matches any characters except .
        # ** matches any characters including .
        regex_pattern = pattern.replace(".", r"\.")
        regex_pattern = regex_pattern.replace("**", "DOUBLE_STAR")
        regex_pattern = regex_pattern.replace("*", "[^.]*")
        regex_pattern = regex_pattern.replace("DOUBLE_STAR", ".*")
        regex_pattern = f"^{regex_pattern}$"

        return re.compile(regex_pattern)


class EventManager:
    """High-level event management for infections."""

    def __init__(self, infection_id: str, control_socket_path: str = "/var/run/pandemic.sock"):
        self.infection_id = infection_id
        self.control_socket_path = control_socket_path
        self.event_client: Optional[EventClient] = None
        self.subscriptions: List[EventSubscription] = []
        self.logger = logging.getLogger(f"{__name__}.manager.{infection_id}")

    async def initialize(self):
        """Initialize event client and register subscriptions."""
        self.event_client = EventClient(self.infection_id)

        # Register subscriptions with core daemon
        if self.subscriptions:
            await self._register_subscriptions()

    async def add_subscription(self, source: str, pattern: str, handler: Callable):
        """Add a new event subscription."""
        subscription = EventSubscription(source, pattern)
        self.subscriptions.append(subscription)

        if self.event_client:
            await self.event_client.subscribe(source, pattern, handler)
            await self._register_subscriptions()

    async def remove_subscription(self, source: str, pattern: str):
        """Remove an event subscription."""
        self.subscriptions = [
            s for s in self.subscriptions if not (s.source == source and s.pattern == pattern)
        ]

        if self.event_client:
            await self.event_client.unsubscribe(source, pattern)
            await self._register_subscriptions()

    async def publish(self, event_type: str, payload: Dict[str, Any]):
        """Publish an event."""
        if not self.event_client:
            raise RuntimeError("Event client not initialized")

        await self.event_client.publish(event_type, payload)

    async def close(self):
        """Close event manager."""
        if self.event_client:
            await self.event_client.close()

    async def _register_subscriptions(self):
        """Register subscriptions with core daemon via control socket."""
        try:
            reader, writer = await asyncio.open_unix_connection(self.control_socket_path)

            # Create subscription message
            message = {
                "id": "subscription-update",
                "command": "subscribeEvents",
                "payload": {
                    "infectionId": self.infection_id,
                    "subscriptions": [
                        {"source": s.source, "pattern": s.pattern} for s in self.subscriptions
                    ],
                },
            }

            # Send message
            message_data = json.dumps(message).encode("utf-8")
            message_length = len(message_data).to_bytes(4, "big")

            writer.write(message_length + message_data)
            await writer.drain()

            # Read response
            length_data = await reader.readexactly(4)
            response_length = int.from_bytes(length_data, "big")
            response_data = await reader.readexactly(response_length)
            response = json.loads(response_data.decode("utf-8"))

            writer.close()
            await writer.wait_closed()

            if response.get("status") != "success":
                self.logger.error(f"Failed to register subscriptions: {response}")
            else:
                self.logger.debug("Subscriptions registered successfully")

        except Exception as e:
            self.logger.error(f"Failed to register subscriptions: {e}")
