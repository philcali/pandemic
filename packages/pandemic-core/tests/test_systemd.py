"""Tests for systemd integration."""

from unittest.mock import AsyncMock, patch

import pytest
from pandemic_core.systemd import SystemdManager


class TestSystemdManager:
    """Test systemd integration."""

    @pytest.fixture
    def systemd_manager(self, test_config):
        """SystemdManager fixture."""
        return SystemdManager(test_config)

    @pytest.mark.asyncio
    async def test_create_service(self, systemd_manager):
        """Test creating systemd service."""
        infection_data = {
            "name": "test-infection",
            "environment": {"DEBUG": "true"},
            "resources": {"memoryLimit": "128M"},
        }

        with (
            patch.object(systemd_manager.helper_client, "connect", new_callable=AsyncMock),
            patch.object(systemd_manager.helper_client, "disconnect", new_callable=AsyncMock),
            patch.object(systemd_manager.helper_client, "create_service", new_callable=AsyncMock),
        ):
            service_name = await systemd_manager.create_service("test-123", infection_data)

            assert service_name == "pandemic-infection@test-infection.service"
            systemd_manager.helper_client.create_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_service(self, systemd_manager):
        """Test removing systemd service."""
        service_name = "pandemic-infection@test.service"

        with (
            patch.object(systemd_manager.helper_client, "connect", new_callable=AsyncMock),
            patch.object(systemd_manager.helper_client, "disconnect", new_callable=AsyncMock),
            patch.object(systemd_manager.helper_client, "remove_service", new_callable=AsyncMock),
        ):
            await systemd_manager.remove_service(service_name)

            systemd_manager.helper_client.remove_service.assert_called_once_with(service_name)

    @pytest.mark.asyncio
    async def test_start_service(self, systemd_manager):
        """Test starting systemd service."""
        with (
            patch.object(systemd_manager.helper_client, "connect", new_callable=AsyncMock),
            patch.object(systemd_manager.helper_client, "disconnect", new_callable=AsyncMock),
            patch.object(systemd_manager.helper_client, "start_service", new_callable=AsyncMock),
        ):
            await systemd_manager.start_service("test.service")
            systemd_manager.helper_client.start_service.assert_called_once_with("test.service")

    @pytest.mark.asyncio
    async def test_get_service_status(self, systemd_manager):
        """Test getting service status."""
        mock_response = {
            "activeState": "active",
            "subState": "running",
            "pid": 12345,
            "memoryUsage": "67108864",
        }

        with (
            patch.object(systemd_manager.helper_client, "connect", new_callable=AsyncMock),
            patch.object(systemd_manager.helper_client, "disconnect", new_callable=AsyncMock),
            patch.object(
                systemd_manager.helper_client,
                "get_status",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            status = await systemd_manager.get_service_status("test.service")

            assert status["activeState"] == "active"
            assert status["subState"] == "running"
            assert status["pid"] == 12345
            assert status["memoryUsage"] == "64.0MB"

    @pytest.mark.asyncio
    async def test_get_service_logs(self, systemd_manager):
        """Test getting service logs."""
        mock_response = {"logs": [{"message": "Test log", "level": "6", "timestamp": "123456"}]}

        with (
            patch.object(systemd_manager.helper_client, "connect", new_callable=AsyncMock),
            patch.object(systemd_manager.helper_client, "disconnect", new_callable=AsyncMock),
            patch.object(
                systemd_manager.helper_client,
                "get_logs",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            logs = await systemd_manager.get_service_logs("test.service", 10)

            assert len(logs) == 1
            assert logs[0]["message"] == "Test log"
            assert logs[0]["level"] == "INFO"

    def test_format_memory(self, systemd_manager):
        """Test memory formatting."""
        assert systemd_manager._format_memory("0") == "0B"
        assert systemd_manager._format_memory("1024") == "1.0KB"
        assert systemd_manager._format_memory("1048576") == "1.0MB"
        assert systemd_manager._format_memory("1073741824") == "1.0GB"

    def test_map_syslog_level(self, systemd_manager):
        """Test syslog level mapping."""
        assert systemd_manager._map_syslog_level("0") == "EMERG"
        assert systemd_manager._map_syslog_level("3") == "ERROR"
        assert systemd_manager._map_syslog_level("6") == "INFO"
        assert systemd_manager._map_syslog_level("7") == "DEBUG"
        assert systemd_manager._map_syslog_level("99") == "INFO"  # Unknown maps to INFO

    def test_generate_override_config(self, systemd_manager):
        """Test generating systemd override configuration."""
        infection_data = {
            "environment": {"DEBUG": "true", "LOG_LEVEL": "INFO"},
            "resources": {"memoryLimit": "128M", "cpuQuota": "50%"},
        }

        config = systemd_manager._generate_override_config(infection_data)

        assert "[Service]" in config
        assert 'Environment="DEBUG=true"' in config
        assert 'Environment="LOG_LEVEL=INFO"' in config
        assert f'Environment="PANDEMIC_SOCKET={systemd_manager.config.socket_path}"' in config
        assert "MemoryLimit=128M" in config
        assert "CPUQuota=50%" in config
