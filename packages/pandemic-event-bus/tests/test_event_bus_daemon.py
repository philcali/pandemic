import asyncio
from unittest.mock import AsyncMock, patch

import pytest


class TestEventDaemon:
    """Test EventDaemon functionality."""

    @pytest.mark.asyncio
    async def test_daemon_initialization(self, event_daemon):
        """Test daemon initialization."""
        assert event_daemon.events_dir is not None
        assert event_daemon.rate_limit == 100
        assert event_daemon.burst_size == 200
        assert len(event_daemon.sockets) == 0

    @pytest.mark.asyncio
    async def test_daemon_startup_creates_core_socket(self, event_daemon):
        """Test daemon startup creates core socket."""
        with patch.object(
            event_daemon, "_create_event_socket", new_callable=AsyncMock
        ) as mock_create:
            await event_daemon.on_startup()

            mock_create.assert_called_once_with("core")

    @pytest.mark.asyncio
    async def test_daemon_shutdown_stops_sockets(self, event_daemon, mock_event_socket):
        """Test daemon shutdown stops all sockets."""
        event_daemon.sockets["test"] = mock_event_socket

        await event_daemon.on_shutdown()

        mock_event_socket.stop.assert_called_once()
        assert len(event_daemon.sockets) == 0

    @pytest.mark.asyncio
    async def test_handle_publish_creates_source_if_needed(self, event_daemon):
        """Test publish handler creates source if it doesn't exist."""
        mock_socket = AsyncMock()
        mock_socket.subscribers = set()
        mock_socket.publish = AsyncMock()

        # Mock the _create_event_socket method to add socket to daemon.sockets
        async def mock_create_socket(source_id):
            event_daemon.sockets[source_id] = mock_socket
            return mock_socket

        with patch.object(
            event_daemon, "_create_event_socket", side_effect=mock_create_socket
        ) as mock_create:
            payload = {
                "sourceId": "new-source",
                "eventType": "test.event",
                "payload": {"key": "value"},
            }

            result = await event_daemon.handle_publish(payload)

            mock_create.assert_called_once_with("new-source")
            mock_socket.publish.assert_called_once()
            assert result["published"] is True
            assert result["sourceId"] == "new-source"

    @pytest.mark.asyncio
    async def test_handle_publish_missing_parameters(self, event_daemon):
        """Test publish handler with missing parameters."""
        # Missing sourceId
        with pytest.raises(ValueError, match="sourceId and eventType are required"):
            await event_daemon.handle_publish({"eventType": "test.event"})

        # Missing eventType
        with pytest.raises(ValueError, match="sourceId and eventType are required"):
            await event_daemon.handle_publish({"sourceId": "test-source"})

    @pytest.mark.asyncio
    async def test_handle_create_source_new(self, event_daemon):
        """Test create source handler for new source."""
        with patch.object(
            event_daemon, "_create_event_socket", new_callable=AsyncMock
        ) as mock_create:
            mock_socket = AsyncMock()
            mock_socket.socket_path = "/tmp/test.sock"
            mock_create.return_value = mock_socket

            payload = {"sourceId": "new-source"}
            result = await event_daemon.handle_create_source(payload)

            mock_create.assert_called_once_with("new-source")
            assert result["created"] is True
            assert result["sourceId"] == "new-source"
            assert result["socketPath"] == "/tmp/test.sock"

    @pytest.mark.asyncio
    async def test_handle_create_source_existing(self, event_daemon, mock_event_socket):
        """Test create source handler for existing source."""
        event_daemon.sockets["existing-source"] = mock_event_socket

        payload = {"sourceId": "existing-source"}
        result = await event_daemon.handle_create_source(payload)

        assert result["exists"] is True
        assert result["sourceId"] == "existing-source"

    @pytest.mark.asyncio
    async def test_handle_create_source_missing_id(self, event_daemon):
        """Test create source handler with missing sourceId."""
        with pytest.raises(ValueError, match="sourceId is required"):
            await event_daemon.handle_create_source({})

    @pytest.mark.asyncio
    async def test_handle_get_stats(self, event_daemon, mock_event_socket):
        """Test get stats handler."""
        mock_event_socket.subscribers = {"sub1", "sub2"}
        event_daemon.sockets["test-source"] = mock_event_socket

        result = await event_daemon.handle_get_stats({})

        assert result["totalSources"] == 1
        assert "test-source" in result["sources"]
        assert result["sources"]["test-source"]["subscriberCount"] == 2
        assert result["eventsDir"] == event_daemon.events_dir
        assert result["rateLimit"] == event_daemon.rate_limit

    @pytest.mark.asyncio
    async def test_create_event_socket_new(self, event_daemon):
        """Test creating new event socket."""
        with patch("pandemic_event_bus.daemon.EventSocket") as mock_socket_class:
            mock_socket = AsyncMock()
            mock_socket_class.return_value = mock_socket

            result = await event_daemon._create_event_socket("test-source")

            mock_socket_class.assert_called_once()
            mock_socket.start.assert_called_once()
            assert event_daemon.sockets["test-source"] == mock_socket
            assert result == mock_socket

    @pytest.mark.asyncio
    async def test_create_event_socket_existing(self, event_daemon, mock_event_socket):
        """Test creating event socket that already exists."""
        event_daemon.sockets["existing"] = mock_event_socket

        result = await event_daemon._create_event_socket("existing")

        assert result == mock_event_socket

    @pytest.mark.asyncio
    async def test_create_event_socket_with_rate_limiter(self, event_daemon):
        """Test creating event socket with rate limiter for non-core sources."""
        with (
            patch("pandemic_event_bus.daemon.EventSocket") as mock_socket_class,
            patch("pandemic_event_bus.daemon.RateLimiter") as mock_limiter_class,
        ):

            mock_socket = AsyncMock()
            mock_limiter = AsyncMock()
            mock_socket_class.return_value = mock_socket
            mock_limiter_class.return_value = mock_limiter

            await event_daemon._create_event_socket("non-core-source")

            # Should create rate limiter for non-core sources
            mock_limiter_class.assert_called_once_with(100, 200)

            # Should pass rate limiter to socket
            args, kwargs = mock_socket_class.call_args
            assert args[2] == mock_limiter  # rate_limiter parameter

    @pytest.mark.asyncio
    async def test_create_event_socket_core_no_rate_limiter(self, event_daemon):
        """Test creating core event socket without rate limiter."""
        with patch("pandemic_event_bus.daemon.EventSocket") as mock_socket_class:
            mock_socket = AsyncMock()
            mock_socket_class.return_value = mock_socket

            await event_daemon._create_event_socket("core")

            # Should not create rate limiter for core source
            args, kwargs = mock_socket_class.call_args
            assert args[2] is None  # rate_limiter parameter should be None


class TestEventDaemonIntegration:
    """Integration tests for EventDaemon."""

    @pytest.mark.asyncio
    async def test_daemon_route_registration(self, event_daemon):
        """Test that routes are properly registered."""
        assert "publish" in event_daemon.route_registry.handlers
        assert "createSource" in event_daemon.route_registry.handlers
        assert "getStats" in event_daemon.route_registry.handlers

    @pytest.mark.asyncio
    async def test_full_daemon_lifecycle(self, event_daemon):
        """Test complete daemon start/stop lifecycle."""
        # Mock the socket creation to avoid actual file system operations
        with patch.object(event_daemon, "_create_event_socket", new_callable=AsyncMock):
            # Start daemon
            start_task = asyncio.create_task(event_daemon.start())
            await asyncio.sleep(0.1)

            assert event_daemon.running is True

            # Stop daemon
            await event_daemon.stop()
            start_task.cancel()

            assert event_daemon.running is False
