"""Pytest configuration and fixtures."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pandemic_core.config import DaemonConfig
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
        event_bus_enabled=False,
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
def daemon(test_config):
    """Refactored daemon fixture with mocked systemd."""
    from pandemic_core.daemon import PandemicDaemon

    daemon = PandemicDaemon(test_config)

    # Mock systemd manager to avoid system calls
    daemon.systemd_manager.create_service = AsyncMock(return_value="test.service")
    daemon.systemd_manager.remove_service = AsyncMock()
    daemon.systemd_manager.start_service = AsyncMock()
    daemon.systemd_manager.stop_service = AsyncMock()
    daemon.systemd_manager.restart_service = AsyncMock()
    daemon.systemd_manager.get_service_status = AsyncMock(
        return_value={
            "activeState": "active",
            "subState": "running",
            "pid": 12345,
            "memoryUsage": "64MB",
            "cpuUsage": "5%",
            "uptime": "1h",
        }
    )
    daemon.systemd_manager.get_service_logs = AsyncMock(return_value=[])

    return daemon


@pytest.fixture
def event_loop():
    """Event loop fixture for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
