"""Event client for communicating with event bus daemon."""

import asyncio
import logging
from typing import Any, Dict, Optional

from pandemic_common.protocol import UDSProtocol


class EventClient:
    """Client for publishing events to event bus daemon."""

    def __init__(self, socket_path: str = "/var/run/pandemic/event-bus.sock"):
        self.socket_path = socket_path
        self.logger = logging.getLogger(__name__)
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False

    async def connect(self):
        """Connect to event bus daemon."""
        if self._connected:
            return

        try:
            self._reader, self._writer = await asyncio.open_unix_connection(self.socket_path)
            self._connected = True
            self.logger.debug("Connected to event bus daemon")
        except Exception as e:
            self.logger.debug(f"Failed to connect to event bus: {e}")
            raise ConnectionError(f"Event bus not available: {e}")

    async def disconnect(self):
        """Disconnect from event bus daemon."""
        if not self._connected:
            return

        try:
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
        except Exception as e:
            self.logger.debug(f"Error during disconnect: {e}")
        finally:
            self._reader = None
            self._writer = None
            self._connected = False

    async def publish(
        self, source_id: str, event_type: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish event via event bus daemon."""
        try:
            await self.connect()

            request = UDSProtocol.create_request(
                "publish", {"sourceId": source_id, "eventType": event_type, "payload": payload}
            )

            await UDSProtocol.send_message(self._writer, request)
            response = await UDSProtocol.receive_message(self._reader)

            if response.get("status") == "error":
                raise RuntimeError(f"Event publish failed: {response.get('error')}")

            return response.get("payload", {})

        except Exception as e:
            self.logger.debug(f"Event publish failed: {e}")
            await self.disconnect()
            raise

    async def create_source(self, source_id: str) -> Dict[str, Any]:
        """Create event source via event bus daemon."""
        try:
            await self.connect()

            request = UDSProtocol.create_request("createSource", {"sourceId": source_id})

            await UDSProtocol.send_message(self._writer, request)
            response = await UDSProtocol.receive_message(self._reader)

            if response.get("status") == "error":
                raise RuntimeError(f"Create source failed: {response.get('error')}")

            return response.get("payload", {})

        except Exception as e:
            self.logger.debug(f"Create source failed: {e}")
            await self.disconnect()
            raise

    async def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        try:
            await self.connect()

            request = UDSProtocol.create_request("getStats", {})

            await UDSProtocol.send_message(self._writer, request)
            response = await UDSProtocol.receive_message(self._reader)

            if response.get("status") == "error":
                raise RuntimeError(f"Get stats failed: {response.get('error')}")

            return response.get("payload", {})

        except Exception as e:
            self.logger.debug(f"Get stats failed: {e}")
            await self.disconnect()
            raise
