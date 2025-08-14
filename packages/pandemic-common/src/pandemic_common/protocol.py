"""Protocol utilities for UDS communication."""

import asyncio
import json
from typing import Any, Dict, Optional


class UDSProtocol:
    """Unix Domain Socket protocol utilities."""

    @staticmethod
    async def send_message(writer: asyncio.StreamWriter, message: Dict[str, Any]):
        """Send message over UDS with length prefix."""
        message_data = json.dumps(message).encode("utf-8")
        message_length = len(message_data).to_bytes(4, "big")

        writer.write(message_length + message_data)
        await writer.drain()

    @staticmethod
    async def receive_message(reader: asyncio.StreamReader) -> Dict[str, Any]:
        """Receive message from UDS with length prefix."""
        # Read message length (4 bytes)
        length_data = await reader.readexactly(4)
        message_length = int.from_bytes(length_data, "big")

        # Read message data
        message_data = await reader.readexactly(message_length)
        return json.loads(message_data.decode("utf-8"))

    @staticmethod
    def create_request(
        command: str, payload: Optional[Dict[str, Any]] = None, message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a request message."""
        import uuid
        from datetime import datetime

        return {
            "id": message_id or str(uuid.uuid4()),
            "type": "request",
            "command": command,
            "payload": payload or {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    @staticmethod
    def create_response(
        message_id: str, payload: Optional[Dict[str, Any]] = None, error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a response message."""
        from datetime import datetime

        return {
            "id": message_id,
            "type": "response",
            "status": "error" if error else "success",
            "payload": payload or {},
            "error": error,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
