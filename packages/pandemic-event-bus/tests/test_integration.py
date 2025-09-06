import asyncio

import pytest
from pandemic_common.protocol import UDSProtocol
from pandemic_event_bus.daemon import EventDaemon


class TestEventBusIntegration:
    """Integration tests for event bus daemon."""

    @pytest.mark.asyncio
    async def test_publish_via_socket_communication(self, temp_dir):
        """Test publishing events via actual socket communication."""
        socket_path = str(temp_dir / "event-bus.sock")
        events_dir = str(temp_dir / "events")

        daemon = EventDaemon(socket_path=socket_path, events_dir=events_dir)

        # Start daemon
        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.1)

        try:
            # Connect as client
            reader, writer = await asyncio.open_unix_connection(socket_path)

            # Send publish request
            request = UDSProtocol.create_request(
                "publish",
                {
                    "sourceId": "test-source",
                    "eventType": "test.event",
                    "payload": {"message": "hello world"},
                },
            )

            await UDSProtocol.send_message(writer, request)
            response = await UDSProtocol.receive_message(reader)

            # Verify response
            assert response["status"] == "success"
            payload = response["payload"]
            assert payload["published"] is True
            assert payload["sourceId"] == "test-source"
            assert "eventId" in payload

            writer.close()
            await writer.wait_closed()

        finally:
            await daemon.stop()
            start_task.cancel()

    @pytest.mark.asyncio
    async def test_create_source_via_socket(self, temp_dir):
        """Test creating event source via socket communication."""
        socket_path = str(temp_dir / "event-bus.sock")
        events_dir = str(temp_dir / "events")

        daemon = EventDaemon(socket_path=socket_path, events_dir=events_dir)

        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)

            # Create new source
            request = UDSProtocol.create_request("createSource", {"sourceId": "new-source"})

            await UDSProtocol.send_message(writer, request)
            response = await UDSProtocol.receive_message(reader)

            assert response["status"] == "success"
            payload = response["payload"]
            assert payload["created"] is True
            assert payload["sourceId"] == "new-source"
            assert "socketPath" in payload

            writer.close()
            await writer.wait_closed()

        finally:
            await daemon.stop()
            start_task.cancel()

    @pytest.mark.asyncio
    async def test_get_stats_via_socket(self, temp_dir):
        """Test getting statistics via socket communication."""
        socket_path = str(temp_dir / "event-bus.sock")
        events_dir = str(temp_dir / "events")

        daemon = EventDaemon(socket_path=socket_path, events_dir=events_dir)

        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)

            # Get stats
            request = UDSProtocol.create_request("getStats", {})

            await UDSProtocol.send_message(writer, request)
            response = await UDSProtocol.receive_message(reader)

            assert response["status"] == "success"
            payload = response["payload"]
            assert "totalSources" in payload
            assert "sources" in payload
            assert "eventsDir" in payload
            assert payload["eventsDir"] == events_dir

            writer.close()
            await writer.wait_closed()

        finally:
            await daemon.stop()
            start_task.cancel()

    @pytest.mark.asyncio
    async def test_invalid_command_handling(self, temp_dir):
        """Test handling of invalid commands."""
        socket_path = str(temp_dir / "event-bus.sock")
        events_dir = str(temp_dir / "events")

        daemon = EventDaemon(socket_path=socket_path, events_dir=events_dir)

        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)

            # Send invalid command
            request = UDSProtocol.create_request("invalidCommand", {})

            await UDSProtocol.send_message(writer, request)
            response = await UDSProtocol.receive_message(reader)

            assert response["status"] == "error"
            assert "Unknown command" in response["error"]

            writer.close()
            await writer.wait_closed()

        finally:
            await daemon.stop()
            start_task.cancel()

    @pytest.mark.asyncio
    async def test_multiple_concurrent_clients(self, temp_dir):
        """Test handling multiple concurrent clients."""
        socket_path = str(temp_dir / "event-bus.sock")
        events_dir = str(temp_dir / "events")

        daemon = EventDaemon(socket_path=socket_path, events_dir=events_dir)

        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.1)

        async def client_request(client_id):
            reader, writer = await asyncio.open_unix_connection(socket_path)

            request = UDSProtocol.create_request(
                "publish",
                {
                    "sourceId": f"client-{client_id}",
                    "eventType": "test.event",
                    "payload": {"clientId": client_id},
                },
            )

            await UDSProtocol.send_message(writer, request)
            response = await UDSProtocol.receive_message(reader)

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
                assert response["payload"]["published"] is True

        finally:
            await daemon.stop()
            start_task.cancel()
