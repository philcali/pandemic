"""Tests for Unix daemon server abstraction."""

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
from pandemic_common import UnixDaemonServer, route
from pandemic_common.protocol import UDSProtocol


class FakeDaemon(UnixDaemonServer):
    """Test daemon implementation."""

    @route("ping")
    async def ping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simple ping handler."""
        return {"message": "pong"}

    @route("echo")
    async def echo(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Echo handler."""
        return {"echo": payload.get("message", "")}


@pytest.mark.asyncio
async def test_daemon_routing():
    """Test daemon routing functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        socket_path = Path(tmpdir) / "test.sock"

        daemon = FakeDaemon(str(socket_path))

        # Test route registration
        assert "ping" in daemon.route_registry.handlers
        assert "echo" in daemon.route_registry.handlers

        # Start daemon in background
        server_task = asyncio.create_task(daemon.start())

        # Wait for server to start
        await asyncio.sleep(0.1)

        try:
            # Connect as client
            reader, writer = await asyncio.open_unix_connection(str(socket_path))

            # Test ping command
            ping_request = UDSProtocol.create_request("ping")
            await UDSProtocol.send_message(writer, ping_request)

            ping_response = await UDSProtocol.receive_message(reader)
            assert ping_response["status"] == "success"
            assert ping_response["payload"]["message"] == "pong"

            # Test echo command
            echo_request = UDSProtocol.create_request("echo", {"message": "hello"})
            await UDSProtocol.send_message(writer, echo_request)

            echo_response = await UDSProtocol.receive_message(reader)
            assert echo_response["status"] == "success"
            assert echo_response["payload"]["echo"] == "hello"

            # Test unknown command
            unknown_request = UDSProtocol.create_request("unknown")
            await UDSProtocol.send_message(writer, unknown_request)

            unknown_response = await UDSProtocol.receive_message(reader)
            assert unknown_response["status"] == "error"
            assert "Unknown command" in unknown_response["error"]

            writer.close()
            await writer.wait_closed()

        finally:
            await daemon.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
