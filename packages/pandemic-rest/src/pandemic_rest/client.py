"""UDS client for communicating with pandemic-core daemon."""

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


class PandemicClient:
    """Client for communicating with pandemic-core via Unix Domain Socket."""

    def __init__(self, socket_path: str = "/var/run/pandemic.sock"):
        self.socket_path = Path(socket_path)
        self.logger = logging.getLogger(__name__)

    async def send_message(self, command: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send message to pandemic daemon and return response."""
        if payload is None:
            payload = {}

        message = {"id": str(uuid.uuid4()), "command": command, "payload": payload}

        try:
            reader, writer = await asyncio.open_unix_connection(str(self.socket_path))

            # Send message
            message_json = json.dumps(message) + "\n"
            writer.write(message_json.encode())
            await writer.drain()

            # Read response
            response_data = await reader.readline()
            writer.close()
            await writer.wait_closed()

            if not response_data:
                raise RuntimeError("No response from daemon")

            response = json.loads(response_data.decode().strip())

            if response.get("status") == "error":
                raise RuntimeError(response.get("error", "Unknown error"))

            return response

        except FileNotFoundError:
            raise RuntimeError(f"Daemon socket not found: {self.socket_path}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {e}")
        except Exception as e:
            self.logger.error(f"UDS communication error: {e}")
            raise RuntimeError(f"Communication error: {e}")

    async def health_check(self, infection_id: Optional[str] = None) -> Dict[str, Any]:
        """Check daemon or infection health."""
        payload = {}
        if infection_id:
            payload["infectionId"] = infection_id

        response = await self.send_message("health", payload)
        return response["payload"]

    async def get_status(self, infection_id: Optional[str] = None) -> Dict[str, Any]:
        """Get daemon or infection status."""
        payload = {}
        if infection_id:
            payload["infectionId"] = infection_id

        response = await self.send_message("status", payload)
        return response["payload"]

    async def list_infections(self, filter_state: Optional[str] = None) -> Dict[str, Any]:
        """List all infections."""
        payload = {}
        if filter_state:
            payload["filter"] = {"state": filter_state}

        response = await self.send_message("list", payload)
        return response["payload"]

    async def install_infection(
        self,
        source: str,
        name: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Install infection from source."""
        payload = {"source": source}
        if name:
            payload["name"] = name
        if config_overrides:
            payload["configOverrides"] = config_overrides

        response = await self.send_message("install", payload)
        return response["payload"]

    async def remove_infection(self, infection_id: str, cleanup: bool = True) -> Dict[str, Any]:
        """Remove infection."""
        payload = {"infectionId": infection_id, "cleanup": cleanup}
        response = await self.send_message("remove", payload)
        return response["payload"]

    async def start_infection(self, infection_id: str) -> Dict[str, Any]:
        """Start infection."""
        payload = {"infectionId": infection_id}
        response = await self.send_message("start", payload)
        return response["payload"]

    async def stop_infection(self, infection_id: str) -> Dict[str, Any]:
        """Stop infection."""
        payload = {"infectionId": infection_id}
        response = await self.send_message("stop", payload)
        return response["payload"]

    async def restart_infection(self, infection_id: str) -> Dict[str, Any]:
        """Restart infection."""
        payload = {"infectionId": infection_id}
        response = await self.send_message("restart", payload)
        return response["payload"]

    async def get_logs(self, infection_id: str, lines: int = 100) -> Dict[str, Any]:
        """Get infection logs."""
        payload = {"infectionId": infection_id, "lines": lines}
        response = await self.send_message("logs", payload)
        return response["payload"]
