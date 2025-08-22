"""Tests for request validator."""

import pytest
from pandemic_systemd_helper.validator import RequestValidator


class TestRequestValidator:
    """Test request validation."""

    @pytest.fixture
    def validator(self):
        """RequestValidator fixture."""
        return RequestValidator()

    def test_validate_valid_request(self, validator):
        """Test validating valid request."""
        request = {
            "command": "startService",
            "payload": {"serviceName": "pandemic-infection@test.service"},
        }

        # Should not raise exception
        validator.validate_request(request)

    def test_validate_invalid_command(self, validator):
        """Test invalid command rejection."""
        request = {
            "command": "invalidCommand",
            "payload": {"serviceName": "pandemic-infection@test.service"},
        }

        with pytest.raises(ValueError, match="Invalid command"):
            validator.validate_request(request)

    def test_validate_invalid_service_name(self, validator):
        """Test invalid service name rejection."""
        request = {
            "command": "startService",
            "payload": {"serviceName": "malicious-service.service"},
        }

        with pytest.raises(ValueError, match="Invalid service name"):
            validator.validate_request(request)

    def test_validate_dangerous_content(self, validator):
        """Test dangerous content detection."""
        request = {
            "command": "createService",
            "payload": {
                "serviceName": "pandemic-infection@test.service",
                "templateContent": "ExecStart=/bin/rm -rf /",
            },
        }

        with pytest.raises(ValueError, match="Invalid template content"):
            validator.validate_request(request)
