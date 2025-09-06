import json

import pytest
from pandemic_event_bus.events import Event, EventSocket, RateLimiter


class TestEvent:
    """Test Event class."""

    def test_create_event(self):
        """Test event creation."""
        event = Event.create("test-source", "test.event", {"key": "value"})

        assert event.source == "test-source"
        assert event.type == "test.event"
        assert event.payload == {"key": "value"}
        assert event.version == "1.0.0"
        assert event.eventId is not None
        assert event.timestamp is not None

    def test_event_serialization(self):
        """Test event JSON serialization."""
        event = Event.create("test-source", "test.event", {"key": "value"})

        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed["source"] == "test-source"
        assert parsed["type"] == "test.event"
        assert parsed["payload"] == {"key": "value"}

    def test_event_deserialization(self):
        """Test event JSON deserialization."""
        original = Event.create("test-source", "test.event", {"key": "value"})
        json_str = original.to_json()

        restored = Event.from_json(json_str)

        assert restored.source == original.source
        assert restored.type == original.type
        assert restored.payload == original.payload
        assert restored.eventId == original.eventId


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_rate_limiter_allows_initial_events(self):
        """Test rate limiter allows events within burst size."""
        limiter = RateLimiter(max_events_per_second=10, burst_size=5)

        # Should allow up to burst_size events
        for _ in range(5):
            assert limiter.allow_event() is True

        # Should deny the next event
        assert limiter.allow_event() is False

    def test_rate_limiter_refills_tokens(self):
        """Test rate limiter refills tokens over time."""
        limiter = RateLimiter(max_events_per_second=10, burst_size=2)

        # Consume all tokens
        assert limiter.allow_event() is True
        assert limiter.allow_event() is True
        assert limiter.allow_event() is False

        # Simulate time passing (0.2 seconds = 2 tokens at 10/sec)
        limiter.last_refill -= 0.2

        # Should allow events again
        assert limiter.allow_event() is True
        assert limiter.allow_event() is True
        assert limiter.allow_event() is False


class TestEventSocket:
    """Test EventSocket class."""

    @pytest.fixture
    def event_socket(self, temp_dir):
        """Event socket fixture."""
        socket_path = str(temp_dir / "test.sock")
        return EventSocket(socket_path, "test-source")

    @pytest.mark.asyncio
    async def test_event_socket_creation(self, event_socket):
        """Test event socket creation."""
        assert event_socket.source_id == "test-source"
        assert event_socket.server is None
        assert len(event_socket.subscribers) == 0

    @pytest.mark.asyncio
    async def test_event_socket_start_stop(self, event_socket):
        """Test event socket start and stop."""
        await event_socket.start()

        assert event_socket.server is not None

        await event_socket.stop()

        # Server object still exists but is closed
        assert event_socket.server is not None

    @pytest.mark.asyncio
    async def test_publish_with_no_subscribers(self, event_socket):
        """Test publishing with no subscribers."""
        await event_socket.start()

        event = Event.create("test-source", "test.event", {"key": "value"})

        # Should not raise an error
        await event_socket.publish(event)

        await event_socket.stop()

    @pytest.mark.asyncio
    async def test_publish_with_rate_limiting(self, temp_dir):
        """Test publishing with rate limiting."""
        socket_path = str(temp_dir / "test.sock")
        rate_limiter = RateLimiter(max_events_per_second=1, burst_size=1)

        event_socket = EventSocket(socket_path, "test-source", rate_limiter)
        await event_socket.start()

        event1 = Event.create("test-source", "test.event1", {})
        event2 = Event.create("test-source", "test.event2", {})

        # First event should be allowed
        await event_socket.publish(event1)

        # Second event should be rate limited (no error, just dropped)
        await event_socket.publish(event2)

        await event_socket.stop()
