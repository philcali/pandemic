"""Pandemic daemon client for UDS communication."""

import asyncio
from typing import Any, Dict, Optional

from pandemic_common.protocol import UDSProtocol


class PandemicClient:
    """Client for communicating with pandemic daemon."""

    def __init__(self, socket_path: str = "/var/run/pandemic.sock"):
        self.socket_path = socket_path
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self):
        """Connect to the pandemic daemon."""
        self.reader, self.writer = await asyncio.open_unix_connection(self.socket_path)

    async def disconnect(self):
        """Disconnect from the daemon."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def send_command(
        self, command: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send command to daemon and return response."""
        if not self.reader or not self.writer:
            raise RuntimeError("Not connected to daemon")

        # Create and send request
        request = UDSProtocol.create_request(command, payload)
        await UDSProtocol.send_message(self.writer, request)

        # Receive response
        response = await UDSProtocol.receive_message(self.reader)
        return response

    async def health_check(self) -> Dict[str, Any]:
        """Check daemon health."""
        return await self.send_command("health")

    async def list_infections(self, filter_state: Optional[str] = None) -> Dict[str, Any]:
        """List all infections."""
        payload = {}
        if filter_state:
            payload["filter"] = {"state": filter_state}
        return await self.send_command("list", payload)

    async def get_status(self, infection_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of daemon or specific infection."""
        payload = {}
        if infection_id:
            payload["infectionId"] = infection_id
        return await self.send_command("status", payload)

    async def install_infection(
        self,
        source: str,
        name: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Install new infection."""
        payload: Dict[str, Any] = {"source": source}
        if name:
            payload["name"] = name
        if config_overrides:
            payload["configOverrides"] = config_overrides
        return await self.send_command("install", payload)

    async def remove_infection(self, infection_id: str, cleanup: bool = True) -> Dict[str, Any]:
        """Remove infection."""
        payload = {"infectionId": infection_id, "cleanup": cleanup}
        return await self.send_command("remove", payload)

    async def start_infection(self, infection_id: str) -> Dict[str, Any]:
        """Start infection."""
        payload = {"infectionId": infection_id}
        return await self.send_command("start", payload)

    async def stop_infection(self, infection_id: str) -> Dict[str, Any]:
        """Stop infection."""
        payload = {"infectionId": infection_id}
        return await self.send_command("stop", payload)

    async def restart_infection(self, infection_id: str) -> Dict[str, Any]:
        """Restart infection."""
        payload = {"infectionId": infection_id}
        return await self.send_command("restart", payload)

    async def get_logs(self, infection_id: str, lines: int = 100) -> Dict[str, Any]:
        """Get infection logs."""
        payload = {"infectionId": infection_id, "lines": lines}
        return await self.send_command("logs", payload)

    async def get_metrics(self, infection_id: Optional[str] = None) -> Dict[str, Any]:
        """Get system or infection metrics."""
        payload = {}
        if infection_id:
            payload["infectionId"] = infection_id
        return await self.send_command("metrics", payload)
