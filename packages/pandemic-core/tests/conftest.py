"""Pytest configuration and fixtures."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pandemic_core.config import DaemonConfig
from pandemic_core.daemon import PandemicDaemon
from pandemic_core.state import StateManager


@pytest.fixture
def temp_dir():
    """Temporary directory fixture."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_dir):
    """Test daemon configuration."""
    return DaemonConfig(
        socket_path=str(temp_dir / "test.sock"),
        state_dir=str(temp_dir),
        infections_dir=str(temp_dir / "infections"),
        config_dir=str(temp_dir / "config"),
        log_level="DEBUG",
        validate_signatures=False,
    )


@pytest.fixture
def state_manager(test_config):
    """State manager fixture."""
    return StateManager(test_config)


@pytest.fixture
def mock_systemd_manager():
    """Mock systemd manager."""
    mock = MagicMock()
    mock.create_service = AsyncMock(return_value="test-service.service")
    mock.remove_service = AsyncMock()
    mock.start_service = AsyncMock()
    mock.stop_service = AsyncMock()
    mock.restart_service = AsyncMock()
    mock.get_service_status = AsyncMock(
        return_value={
            "activeState": "active",
            "subState": "running",
            "pid": 12345,
            "memoryUsage": "64MB",
            "cpuUsage": "5%",
            "uptime": "1h 30m",
        }
    )
    mock.get_service_logs = AsyncMock(return_value=[])
    return mock


@pytest.fixture
async def daemon(test_config, monkeypatch):
    """Daemon fixture with mocked systemd."""
    # Mock systemd manager to avoid system calls
    mock_systemd = MagicMock()
    mock_systemd.create_service = AsyncMock(return_value="test.service")
    mock_systemd.remove_service = AsyncMock()
    mock_systemd.start_service = AsyncMock()
    mock_systemd.stop_service = AsyncMock()
    mock_systemd.restart_service = AsyncMock()
    mock_systemd.get_service_status = AsyncMock(
        return_value={
            "activeState": "active",
            "subState": "running",
            "pid": 12345,
            "memoryUsage": "64MB",
            "cpuUsage": "5%",
            "uptime": "1h",
        }
    )
    mock_systemd.get_service_logs = AsyncMock(return_value=[])

    daemon = PandemicDaemon(test_config)
    daemon.message_handler.systemd_manager = mock_systemd

    return daemon


@pytest.fixture
def event_loop():
    """Event loop fixture for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
