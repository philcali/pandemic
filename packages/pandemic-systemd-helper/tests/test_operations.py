"""Tests for systemd operations."""

import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pandemic_systemd_helper.operations import SystemdOperations


class TestSystemdOperations:
    """Test systemd operations."""

    @pytest.fixture
    def operations(self):
        """SystemdOperations fixture."""
        return SystemdOperations()

    @pytest.mark.asyncio
    async def test_create_service(self, operations):
        """Test creating systemd service."""
        with (
            patch("pathlib.Path.write_text"),
            patch("pathlib.Path.mkdir"),
            patch.object(operations, "_run_systemctl", new_callable=AsyncMock),
        ):
            result = await operations.create_service(
                "pandemic-infection@test.service",
                "[Unit]\nDescription=Test",
                "[Service]\nEnvironment=TEST=1",
            )

            assert result["status"] == "success"
            assert result["operation"] == "created"

    @pytest.mark.asyncio
    async def test_start_service(self, operations):
        """Test starting systemd service."""
        with patch.object(operations, "_run_systemctl", new_callable=AsyncMock):
            result = await operations.start_service("test.service")

            assert result["status"] == "success"
            assert result["operation"] == "started"
            operations._run_systemctl.assert_called_once_with("start", "test.service")

    @pytest.mark.asyncio
    async def test_get_status(self, operations):
        """Test getting service status."""
        mock_result = MagicMock()
        mock_result.stdout = (
            "ActiveState=active\nSubState=running\nMainPID=12345\nMemoryCurrent=67108864"
        )

        with patch.object(
            operations, "_run_systemctl", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await operations.get_status("test.service")

            assert result["status"] == "success"
            assert result["activeState"] == "active"
            assert result["pid"] == 12345
