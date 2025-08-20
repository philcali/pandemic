"""Tests for pandemic-common event client."""

import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pandemic_common.events import EventClient, EventManager, EventSubscription


class TestEventSubscription:
    """Test EventSubscription dataclass."""

    def test_event_subscription_creation(self):
        """Test creating event subscription."""
        sub = EventSubscription("core", "infection.*")
        assert sub.source == "core"
        assert sub.pattern == "infection.*"


class TestEventClient:
    """Test EventClient class."""

    @pytest.fixture
    def temp_events_dir(self):
        """Create temporary events directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_pattern_compilation(self):
        """Test glob pattern compilation to regex."""
        client = EventClient("test-infection")

        # Test simple pattern
        regex = client._compile_pattern("infection.*")
        assert regex.match("infection.started")
        assert regex.match("infection.stopped")
        assert not regex.match("system.health")

        # Test wildcard pattern
        regex = client._compile_pattern("*")
        assert regex.match("started")
        assert regex.match("stopped")
        assert not regex.match("infection.started")

        # Test double wildcard
        regex = client._compile_pattern("**")
        assert regex.match("infection.started")
        assert regex.match("system.health.check")
        assert regex.match("anything")

    @pytest.mark.asyncio
    async def test_publish_event_failure(self, temp_events_dir):
        """Test publish event when socket doesn't exist."""
        client = EventClient("test-infection", temp_events_dir)

        # Should raise exception when socket doesn't exist
        with pytest.raises(Exception):
            await client.publish("test.event", {"key": "value"})

    @pytest.mark.asyncio
    async def test_subscription_lifecycle(self, temp_events_dir):
        """Test subscription lifecycle."""
        client = EventClient("test-infection", temp_events_dir)

        # Mock handler
        handler = AsyncMock()

        # Subscribe (will fail to connect but shouldn't raise)
        await client.subscribe("core", "test.*", handler)
        assert "core:test.*" in client.subscriptions

        # Unsubscribe
        await client.unsubscribe("core", "test.*")
        assert "core:test.*" not in client.subscriptions

        # Close client
        await client.close()
        assert len(client.subscriptions) == 0


class TestEventManager:
    """Test EventManager class."""

    @pytest.fixture
    def temp_control_socket(self):
        """Create temporary control socket path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield os.path.join(temp_dir, "control.sock")

    @pytest.mark.asyncio
    async def test_event_manager_initialization(self, temp_control_socket):
        """Test event manager initialization."""
        manager = EventManager("test-infection", temp_control_socket)

        # Add subscription before initialization
        handler = AsyncMock()
        await manager.add_subscription("core", "infection.*", handler)

        assert len(manager.subscriptions) == 1
        assert manager.subscriptions[0].source == "core"
        assert manager.subscriptions[0].pattern == "infection.*"

    @pytest.mark.asyncio
    async def test_subscription_management(self, temp_control_socket):
        """Test adding and removing subscriptions."""
        manager = EventManager("test-infection", temp_control_socket)
        handler = AsyncMock()

        # Add subscription
        await manager.add_subscription("core", "infection.*", handler)
        assert len(manager.subscriptions) == 1

        # Add another subscription
        await manager.add_subscription("other-infection", "custom.*", handler)
        assert len(manager.subscriptions) == 2

        # Remove subscription
        await manager.remove_subscription("core", "infection.*")
        assert len(manager.subscriptions) == 1
        assert manager.subscriptions[0].source == "other-infection"

    @pytest.mark.asyncio
    async def test_publish_without_initialization(self, temp_control_socket):
        """Test publishing without initialization."""
        manager = EventManager("test-infection", temp_control_socket)

        with pytest.raises(RuntimeError, match="Event client not initialized"):
            await manager.publish("test.event", {"key": "value"})


if __name__ == "__main__":
    pytest.main([__file__])
