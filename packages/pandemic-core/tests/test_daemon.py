"""Tests for daemon functionality."""

import asyncio
import json

import pytest
from pandemic_core.daemon import PandemicDaemon


class TestPandemicDaemon:
    """Test daemon functionality."""

    @pytest.mark.asyncio
    async def test_daemon_start_stop(self, daemon, test_config):
        """Test daemon start and stop."""
        # Start daemon in background
        start_task = asyncio.create_task(daemon.start())

        # Give it time to start
        await asyncio.sleep(0.1)

        assert daemon.running is True

        # Stop daemon
        await daemon.stop()
        start_task.cancel()

        assert daemon.running is False

    @pytest.mark.asyncio
    async def test_client_connection(self, daemon, test_config):
        """Test client can connect and communicate."""
        # Start daemon
        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.1)

        try:
            # Connect as client
            reader, writer = await asyncio.open_unix_connection(test_config.socket_path)

            # Send health check
            message = {"id": "test-1", "type": "request", "command": "health", "payload": {}}

            # Send message
            msg_data = json.dumps(message).encode("utf-8")
            msg_len = len(msg_data).to_bytes(4, "big")
            writer.write(msg_len + msg_data)
            await writer.drain()

            # Read response
            len_data = await reader.readexactly(4)
            resp_len = int.from_bytes(len_data, "big")
            resp_data = await reader.readexactly(resp_len)
            response = json.loads(resp_data.decode("utf-8"))

            assert response["status"] == "success"
            assert response["payload"]["status"] == "healthy"

            writer.close()
            await writer.wait_closed()

        finally:
            await daemon.stop()
            start_task.cancel()

    @pytest.mark.asyncio
    async def test_multiple_clients(self, daemon, test_config):
        """Test multiple clients can connect simultaneously."""
        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.1)

        async def client_request(client_id):
            reader, writer = await asyncio.open_unix_connection(test_config.socket_path)

            message = {"id": f"client-{client_id}", "command": "health", "payload": {}}

            msg_data = json.dumps(message).encode("utf-8")
            msg_len = len(msg_data).to_bytes(4, "big")
            writer.write(msg_len + msg_data)
            await writer.drain()

            len_data = await reader.readexactly(4)
            resp_len = int.from_bytes(len_data, "big")
            resp_data = await reader.readexactly(resp_len)
            response = json.loads(resp_data.decode("utf-8"))

            writer.close()
            await writer.wait_closed()

            return response

        try:
            # Create multiple concurrent clients
            tasks = [client_request(i) for i in range(3)]
            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response["status"] == "success"

        finally:
            await daemon.stop()
            start_task.cancel()

    @pytest.mark.asyncio
    async def test_malformed_message(self, daemon, test_config):
        """Test daemon handles malformed messages gracefully."""
        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(test_config.socket_path)

            # Send malformed JSON
            bad_data = b'{"invalid": json'
            msg_len = len(bad_data).to_bytes(4, "big")
            writer.write(msg_len + bad_data)
            await writer.drain()

            # Connection should close gracefully
            writer.close()
            await writer.wait_closed()

        finally:
            await daemon.stop()
            start_task.cancel()
