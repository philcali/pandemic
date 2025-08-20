"""Tests for event bus system."""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest
from pandemic_core.events import Event, EventBusManager, EventSocket, RateLimiter


class TestEvent:
    """Test Event class."""

    def test_create_event(self):
        """Test event creation."""
        event = Event.create("test-source", "test.event", {"key": "value"})

        assert event.source == "test-source"
        assert event.type == "test.event"
        assert event.version == "1.0.0"
        assert event.payload == {"key": "value"}
        assert event.eventId is not None
        assert event.timestamp is not None

    def test_event_serialization(self):
        """Test event JSON serialization."""
        event = Event.create("test-source", "test.event", {"key": "value"})

        # Serialize to JSON
        json_str = event.to_json()
        assert isinstance(json_str, str)

        # Deserialize from JSON
        event2 = Event.from_json(json_str)
        assert event2.eventId == event.eventId
        assert event2.source == event.source
        assert event2.type == event.type
        assert event2.payload == event.payload

    def test_event_with_custom_version(self):
        """Test event with custom version."""
        event = Event.create("test-source", "test.event", {}, version="2.0.0")
        assert event.version == "2.0.0"


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_rate_limiter_allows_initial_events(self):
        """Test rate limiter allows events within burst."""
        limiter = RateLimiter(10, 5)  # 10 events/sec, burst of 5

        # Should allow burst events
        for _ in range(5):
            assert limiter.allow_event() is True

        # Should deny next event
        assert limiter.allow_event() is False

    def test_rate_limiter_refills_tokens(self):
        """Test rate limiter refills tokens over time."""
        limiter = RateLimiter(10, 2)  # 10 events/sec, burst of 2

        # Consume all tokens
        assert limiter.allow_event() is True
        assert limiter.allow_event() is True
        assert limiter.allow_event() is False

        # Wait for token refill (0.1 seconds = 1 token at 10/sec)
        time.sleep(0.15)
        assert limiter.allow_event() is True


class TestEventSocket:
    """Test EventSocket class."""

    @pytest.fixture
    def temp_socket_path(self):
        """Create temporary socket path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield os.path.join(temp_dir, "test.sock")

    @pytest.mark.asyncio
    async def test_event_socket_lifecycle(self, temp_socket_path):
        """Test event socket start/stop lifecycle."""
        socket = EventSocket(temp_socket_path, "test-source")

        # Start socket
        await socket.start()
        assert Path(temp_socket_path).exists()
        assert socket.server is not None

        # Stop socket
        await socket.stop()
        assert not Path(temp_socket_path).exists()
        assert not socket.server.is_serving()

    @pytest.mark.asyncio
    async def test_event_socket_publish_no_subscribers(self, temp_socket_path):
        """Test publishing event with no subscribers."""
        socket = EventSocket(temp_socket_path, "test-source")
        await socket.start()

        try:
            event = Event.create("test-source", "test.event", {})
            # Should not raise exception
            await socket.publish(event)
        finally:
            await socket.stop()

    @pytest.mark.asyncio
    async def test_event_socket_rate_limiting(self, temp_socket_path):
        """Test event socket rate limiting."""
        rate_limiter = RateLimiter(1, 1)  # Very restrictive
        socket = EventSocket(temp_socket_path, "test-source", rate_limiter)
        await socket.start()

        try:
            event1 = Event.create("test-source", "test.event1", {})
            event2 = Event.create("test-source", "test.event2", {})

            # First event should be allowed
            await socket.publish(event1)

            # Second event should be rate limited (logged but not fail)
            await socket.publish(event2)

        finally:
            await socket.stop()


class TestEventBusManager:
    """Test EventBusManager class."""

    @pytest.fixture
    def temp_events_dir(self):
        """Create temporary events directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.mark.asyncio
    async def test_event_bus_manager_lifecycle(self, temp_events_dir):
        """Test event bus manager start/stop."""
        manager = EventBusManager(temp_events_dir)

        await manager.start()
        assert "core" in manager.sockets
        assert Path(temp_events_dir).exists()

        await manager.stop()
        assert len(manager.sockets) == 0

    @pytest.mark.asyncio
    async def test_create_remove_event_socket(self, temp_events_dir):
        """Test creating and removing event sockets."""
        manager = EventBusManager(temp_events_dir)
        await manager.start()

        try:
            # Create infection socket
            socket = await manager.create_event_socket("infection-123")
            assert "infection-123" in manager.sockets
            assert socket.source_id == "infection-123"

            # Remove infection socket
            await manager.remove_event_socket("infection-123")
            assert "infection-123" not in manager.sockets

        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_publish_event(self, temp_events_dir):
        """Test publishing events."""
        manager = EventBusManager(temp_events_dir)
        await manager.start()

        try:
            # Publish to core socket
            await manager.publish_event("core", "test.event", {"key": "value"})

            # Publish to non-existent socket (should log warning)
            await manager.publish_event("non-existent", "test.event", {})

        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_get_stats(self, temp_events_dir):
        """Test getting event bus statistics."""
        manager = EventBusManager(temp_events_dir, rate_limit=50, burst_size=100)
        await manager.start()

        try:
            await manager.create_event_socket("infection-123")

            stats = manager.get_stats()
            assert stats["totalSources"] == 2  # core + infection-123
            assert "core" in stats["sources"]
            assert "infection-123" in stats["sources"]
            assert stats["rateLimit"] == 50
            assert stats["burstSize"] == 100

        finally:
            await manager.stop()


@pytest.mark.skipif(sys.version_info > (3, 12), reason="Broken in 3.12 and it hangs")
class TestEventBusIntegration:
    """Integration tests for event bus system."""

    @pytest.fixture
    def temp_events_dir(self):
        """Create temporary events directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.mark.asyncio
    async def test_end_to_end_event_flow(self, temp_events_dir):
        """Test complete event publishing and subscription flow."""
        manager = EventBusManager(temp_events_dir)
        await manager.start()

        try:
            # Create infection socket
            await manager.create_event_socket("infection-123")

            # Simulate subscriber connection
            socket_path = manager.get_socket_path("core")
            assert socket_path is not None

            # Connect as subscriber
            reader, writer = await asyncio.open_unix_connection(socket_path)

            try:
                # Publish event
                await asyncio.sleep(1.0)
                await manager.publish_event("core", "test.event", {"message": "hello"})

                # Read event (with timeout)
                try:
                    length_data = await asyncio.wait_for(reader.readexactly(4), timeout=1.0)
                    event_length = int.from_bytes(length_data, "big")
                    event_data = await asyncio.wait_for(
                        reader.readexactly(event_length), timeout=1.0
                    )

                    event_json = event_data.decode("utf-8")
                    event_dict = json.loads(event_json)

                    assert event_dict["source"] == "core"
                    assert event_dict["type"] == "test.event"
                    assert event_dict["payload"]["message"] == "hello"

                except asyncio.TimeoutError:
                    pytest.fail("Did not receive event within timeout")

            finally:
                writer.close()
                await writer.wait_closed()

        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, temp_events_dir):
        """Test event delivery to multiple subscribers."""
        manager = EventBusManager(temp_events_dir)
        await manager.start()

        try:
            socket_path = manager.get_socket_path("core")

            # Connect multiple subscribers
            subscribers = []
            for i in range(3):
                reader, writer = await asyncio.open_unix_connection(socket_path)
                subscribers.append((reader, writer))

            try:
                # Publish event
                await asyncio.sleep(1.0)
                await manager.publish_event("core", "broadcast.test", {"id": 42})

                # All subscribers should receive the event
                for i, (reader, writer) in enumerate(subscribers):
                    try:
                        length_data = await asyncio.wait_for(reader.readexactly(4), timeout=1.0)
                        event_length = int.from_bytes(length_data, "big")
                        event_data = await asyncio.wait_for(
                            reader.readexactly(event_length), timeout=1.0
                        )

                        event_dict = json.loads(event_data.decode("utf-8"))
                        assert event_dict["type"] == "broadcast.test"
                        assert event_dict["payload"]["id"] == 42

                    except asyncio.TimeoutError:
                        pytest.fail(f"Subscriber {i} did not receive event")

            finally:
                for reader, writer in subscribers:
                    writer.close()
                    await writer.wait_closed()

        finally:
            await manager.stop()


class TestEventBusConfiguration:
    """Test event bus configuration and error handling."""

    @pytest.mark.asyncio
    async def test_invalid_socket_path(self):
        """Test handling of invalid socket paths."""
        # Try to create socket in non-existent directory
        manager = EventBusManager("/non/existent/path")

        with pytest.raises(Exception):
            await manager.start()

    @pytest.mark.asyncio
    async def test_permission_handling(self):
        """Test socket permission handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = EventBusManager(temp_dir, socket_mode=0o600, socket_group="nonexistent")

            # Should start despite group not existing (logs warning)
            await manager.start()

            try:
                # Check that core socket was created
                assert "core" in manager.sockets

            finally:
                await manager.stop()


if __name__ == "__main__":
    pytest.main([__file__])
