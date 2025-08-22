"""Client for communicating with privileged systemd helper."""

import asyncio
import logging
from typing import Any, Dict, Optional

from pandemic_common.protocol import UDSProtocol


class SystemdHelperClient:
    """Client for privileged systemd helper daemon."""

    def __init__(self, socket_path: str = "/var/run/pandemic/systemd-helper.sock"):
        self.socket_path = socket_path
        self.logger = logging.getLogger(__name__)
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self):
        """Connect to helper daemon."""
        try:
            self.reader, self.writer = await asyncio.open_unix_connection(self.socket_path)
            self.logger.debug("Connected to systemd helper")
        except Exception as e:
            self.logger.error(f"Failed to connect to systemd helper: {e}")
            raise

    async def disconnect(self):
        """Disconnect from helper daemon."""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                self.logger.warning(f"Error closing connection: {e}")
            finally:
                self.reader = None
                self.writer = None

    async def create_service(
        self,
        service_name: str,
        template_content: str = "",
        override_config: str = "",
        infection_id: str = "",
    ) -> Dict[str, Any]:
        """Create systemd service."""
        request = {
            "command": "createService",
            "payload": {
                "serviceName": service_name,
                "templateContent": template_content,
                "overrideConfig": override_config,
                "infectionId": infection_id,
            },
        }
        return await self._send_request(request)

    async def remove_service(self, service_name: str) -> Dict[str, Any]:
        """Remove systemd service."""
        request = {"command": "removeService", "payload": {"serviceName": service_name}}
        return await self._send_request(request)

    async def start_service(self, service_name: str) -> Dict[str, Any]:
        """Start systemd service."""
        request = {"command": "startService", "payload": {"serviceName": service_name}}
        return await self._send_request(request)

    async def stop_service(self, service_name: str) -> Dict[str, Any]:
        """Stop systemd service."""
        request = {"command": "stopService", "payload": {"serviceName": service_name}}
        return await self._send_request(request)

    async def enable_service(self, service_name: str) -> Dict[str, Any]:
        """Enable systemd service."""
        request = {"command": "enableService", "payload": {"serviceName": service_name}}
        return await self._send_request(request)

    async def disable_service(self, service_name: str) -> Dict[str, Any]:
        """Disable systemd service."""
        request = {"command": "disableService", "payload": {"serviceName": service_name}}
        return await self._send_request(request)

    async def get_status(self, service_name: str) -> Dict[str, Any]:
        """Get systemd service status."""
        request = {"command": "getStatus", "payload": {"serviceName": service_name}}
        return await self._send_request(request)

    async def get_logs(self, service_name: str, lines: int = 100) -> Dict[str, Any]:
        """Get service logs."""
        request = {"command": "getLogs", "payload": {"serviceName": service_name, "lines": lines}}
        return await self._send_request(request)

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to helper daemon."""
        if not self.writer or not self.reader:
            raise RuntimeError("Not connected to systemd helper")

        try:
            # Send request using UDS protocol
            await UDSProtocol.send_message(self.writer, request)

            # Read response using UDS protocol
            response = await UDSProtocol.receive_message(self.reader)

            if response.get("status") == "error":
                raise RuntimeError(f"Helper error: {response.get('error')}")

            return response

        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            raise
