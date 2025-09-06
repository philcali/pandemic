"""Tests for refactored daemon functionality."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from pandemic_common.protocol import UDSProtocol

# Import will be done in fixture to avoid import issues


class TestPandemicDaemon:
    """Test refactored daemon functionality."""

    @pytest.mark.asyncio
    async def test_daemon_start_stop(self, daemon, test_config):
        """Test daemon start and stop."""
        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.1)

        assert daemon.running is True

        await daemon.stop()
        start_task.cancel()
        assert daemon.running is False

    @pytest.mark.asyncio
    async def test_health_check(self, daemon):
        """Test health check route handler."""
        response = await daemon.handle_health({})

        assert response["status"] == "healthy"
        assert response["daemon"] is True

    @pytest.mark.asyncio
    async def test_health_check_infection(self, daemon):
        """Test health check for specific infection."""
        # Add infection to state
        infection_data = {"infectionId": "test-123", "name": "test"}
        daemon.state_manager.add_infection("test-123", infection_data)

        response = await daemon.handle_health({"infectionId": "test-123"})

        assert response["status"] == "healthy"
        assert response["infectionId"] == "test-123"

    @pytest.mark.asyncio
    async def test_list_infections(self, daemon):
        """Test listing infections."""
        # Add test infections
        infections = [
            {"infectionId": "test-1", "name": "test1", "state": "running"},
            {"infectionId": "test-2", "name": "test2", "state": "stopped"},
        ]

        for infection in infections:
            daemon.state_manager.add_infection(infection["infectionId"], infection)

        response = await daemon.handle_list({})

        assert response["totalCount"] == 2
        assert response["runningCount"] == 1
        assert len(response["infections"]) == 2

    @pytest.mark.asyncio
    async def test_install_infection(self, daemon):
        """Test infection installation."""
        # Mock source manager
        daemon.source_manager.install_from_source = AsyncMock(
            return_value={
                "installationPath": "/opt/pandemic/infections/test-infection",
                "downloadInfo": {"source": "github://test/repo@v1.0.0", "type": "github"},
                "configInfo": {"metadata": {"name": "test-infection"}},
            }
        )

        payload = {"source": "github://test/repo@v1.0.0", "name": "test-infection"}
        response = await daemon.handle_install(payload)

        assert "infectionId" in response
        assert response["serviceName"] == "test.service"
        daemon.source_manager.install_from_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_install_without_source(self, daemon):
        """Test installation without source fails."""
        with pytest.raises(ValueError, match="Source is required"):
            await daemon.handle_install({})

    @pytest.mark.asyncio
    async def test_start_infection(self, daemon):
        """Test starting infection."""
        # Add infection to state
        infection_data = {"infectionId": "test-123", "name": "test", "serviceName": "test.service"}
        daemon.state_manager.add_infection("test-123", infection_data)

        response = await daemon.handle_start({"infectionId": "test-123"})

        assert response["status"] == "started"
        daemon.systemd_manager.start_service.assert_called_once_with("test.service")

    @pytest.mark.asyncio
    async def test_client_communication(self, daemon, test_config):
        """Test full client communication via socket."""
        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(test_config.socket_path)

            # Send health check using UDS protocol
            request = UDSProtocol.create_request("health")
            await UDSProtocol.send_message(writer, request)

            # Read response
            response = await UDSProtocol.receive_message(reader)

            assert response["status"] == "success"
            assert response["payload"]["status"] == "healthy"

            writer.close()
            await writer.wait_closed()

        finally:
            await daemon.stop()
            start_task.cancel()

    @pytest.mark.asyncio
    async def test_unknown_command(self, daemon, test_config):
        """Test unknown command returns error."""
        start_task = asyncio.create_task(daemon.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(test_config.socket_path)

            request = UDSProtocol.create_request("unknown")
            await UDSProtocol.send_message(writer, request)

            response = await UDSProtocol.receive_message(reader)

            assert response["status"] == "error"
            assert "Unknown command" in response["error"]

            writer.close()
            await writer.wait_closed()

        finally:
            await daemon.stop()
            start_task.cancel()

    def test_extract_name_from_source(self, daemon):
        """Test extracting name from source URL."""
        assert daemon._extract_name_from_source("github://user/my-repo@v1.0.0") == "my-repo"
        assert daemon._extract_name_from_source("unknown://source") == "unknown"

    def test_map_systemd_state(self, daemon):
        """Test mapping systemd states to infection states."""
        assert daemon._map_systemd_state("active") == "running"
        assert daemon._map_systemd_state("inactive") == "stopped"
        assert daemon._map_systemd_state("failed") == "failed"
        assert daemon._map_systemd_state("unknown") == "unknown"
