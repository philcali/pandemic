"""Pytest configuration and fixtures for event bus tests."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def temp_dir():
    """Temporary directory fixture."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def event_daemon(temp_dir):
    """Event daemon fixture."""
    from pandemic_event_bus.daemon import EventDaemon

    socket_path = str(temp_dir / "event-bus.sock")
    events_dir = str(temp_dir / "events")

    return EventDaemon(
        socket_path=socket_path, events_dir=events_dir, socket_mode=660, socket_group="pandemic"
    )


@pytest.fixture
def mock_event_socket():
    """Mock event socket fixture."""
    mock = MagicMock()
    mock.socket_path = "/tmp/test.sock"
    mock.subscribers = set()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.publish = AsyncMock()
    return mock


@pytest.fixture
def event_loop():
    """Event loop fixture for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
