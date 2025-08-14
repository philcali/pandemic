"""Tests for message handlers."""

import pytest
from pandemic_core.handlers import MessageHandler


class TestMessageHandler:
    """Test message handling."""

    @pytest.fixture
    def handler(self, test_config, state_manager, mock_systemd_manager):
        """Message handler fixture."""
        handler = MessageHandler(test_config, state_manager)
        handler.systemd_manager = mock_systemd_manager
        return handler

    @pytest.mark.asyncio
    async def test_health_check(self, handler):
        """Test health check message."""
        message = {"id": "test-1", "command": "health", "payload": {}}

        response = await handler.handle_message(message)

        assert response["status"] == "success"
        assert response["payload"]["status"] == "healthy"
        assert response["payload"]["daemon"] is True

    @pytest.mark.asyncio
    async def test_health_check_infection(self, handler, state_manager):
        """Test health check for specific infection."""
        # Add infection to state
        infection_data = {"infectionId": "test-123", "name": "test"}
        state_manager.add_infection("test-123", infection_data)

        message = {"id": "test-2", "command": "health", "payload": {"infectionId": "test-123"}}

        response = await handler.handle_message(message)

        assert response["status"] == "success"
        assert response["payload"]["infectionId"] == "test-123"

    @pytest.mark.asyncio
    async def test_list_infections(self, handler, state_manager):
        """Test listing infections."""
        # Add test infections
        infections = [
            {"infectionId": "test-1", "name": "test1", "state": "running"},
            {"infectionId": "test-2", "name": "test2", "state": "stopped"},
        ]

        for infection in infections:
            state_manager.add_infection(infection["infectionId"], infection)

        message = {"id": "test-3", "command": "list", "payload": {}}

        response = await handler.handle_message(message)

        assert response["status"] == "success"
        payload = response["payload"]
        assert payload["totalCount"] == 2
        assert payload["runningCount"] == 1
        assert len(payload["infections"]) == 2

    @pytest.mark.asyncio
    async def test_install_infection(self, handler, mock_systemd_manager):
        """Test infection installation."""
        message = {
            "id": "test-4",
            "command": "install",
            "payload": {"source": "github://test/repo@v1.0.0", "name": "test-infection"},
        }

        response = await handler.handle_message(message)

        assert response["status"] == "success"
        payload = response["payload"]
        assert "infectionId" in payload
        assert payload["serviceName"] == "test-service.service"

        # Verify systemd manager was called
        mock_systemd_manager.create_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_install_without_source(self, handler):
        """Test installation without source fails."""
        message = {"id": "test-5", "command": "install", "payload": {}}

        response = await handler.handle_message(message)

        assert response["status"] == "error"
        assert "Source is required" in response["error"]

    @pytest.mark.asyncio
    async def test_start_infection(self, handler, state_manager, mock_systemd_manager):
        """Test starting infection."""
        # Add infection to state
        infection_data = {"infectionId": "test-123", "name": "test", "serviceName": "test.service"}
        state_manager.add_infection("test-123", infection_data)

        message = {"id": "test-6", "command": "start", "payload": {"infectionId": "test-123"}}

        response = await handler.handle_message(message)

        assert response["status"] == "success"
        assert response["payload"]["status"] == "started"

        # Verify systemd manager was called
        mock_systemd_manager.start_service.assert_called_once_with("test.service")

    @pytest.mark.asyncio
    async def test_unknown_command(self, handler):
        """Test unknown command returns error."""
        message = {"id": "test-7", "command": "unknown", "payload": {}}

        response = await handler.handle_message(message)

        assert response["status"] == "error"
        assert "Unknown command" in response["error"]

    @pytest.mark.asyncio
    async def test_extract_name_from_source(self, handler):
        """Test extracting name from source URL."""
        # Test github source
        name = handler._extract_name_from_source("github://user/my-repo@v1.0.0")
        assert name == "my-repo"

        # Test unknown source
        name = handler._extract_name_from_source("unknown://source")
        assert name == "unknown"

    @pytest.mark.asyncio
    async def test_map_systemd_state(self, handler):
        """Test mapping systemd states to infection states."""
        assert handler._map_systemd_state("active") == "running"
        assert handler._map_systemd_state("inactive") == "stopped"
        assert handler._map_systemd_state("failed") == "failed"
        assert handler._map_systemd_state("unknown") == "unknown"
