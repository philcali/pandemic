"""Request validation for privileged systemd operations."""

import re
from pathlib import Path
from typing import Any, Dict


class RequestValidator:
    """Validates systemd helper requests for security."""

    ALLOWED_SERVICE_PATTERN = re.compile(r"^pandemic-infection@[a-zA-Z0-9_-]+\.service$")
    ALLOWED_COMMANDS = {
        "createService",
        "removeService",
        "startService",
        "stopService",
        "enableService",
        "disableService",
        "getStatus",
        "getLogs",
    }
    MAX_CONTENT_SIZE = 64 * 1024  # 64KB

    def validate_request(self, request: Dict[str, Any]) -> None:
        """Validate incoming request."""
        if not isinstance(request, dict):
            raise ValueError("Request must be a dictionary")

        command = request.get("command")
        if command not in self.ALLOWED_COMMANDS:
            raise ValueError(f"Invalid command: {command}")

        payload = request.get("payload", {})
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a dictionary")

        # Validate based on command type
        if command in [
            "createService",
            "removeService",
            "startService",
            "stopService",
            "enableService",
            "disableService",
            "getStatus",
            "getLogs",
        ]:
            self._validate_service_name(payload.get("serviceName"))

        if command == "createService":
            self._validate_create_service(payload)

    def _validate_service_name(self, service_name: str) -> None:
        """Validate service name matches allowed pattern."""
        if not service_name or not isinstance(service_name, str):
            raise ValueError("Service name is required")

        if not self.ALLOWED_SERVICE_PATTERN.match(service_name):
            raise ValueError(f"Invalid service name: {service_name}")

    def _validate_create_service(self, payload: Dict[str, Any]) -> None:
        """Validate createService payload."""
        template_content = payload.get("templateContent", "")
        override_config = payload.get("overrideConfig", "")

        if len(template_content) > self.MAX_CONTENT_SIZE:
            raise ValueError("Template content too large")

        if len(override_config) > self.MAX_CONTENT_SIZE:
            raise ValueError("Override config too large")

        # Basic content validation
        if template_content and not self._is_safe_systemd_content(template_content):
            raise ValueError("Invalid template content")

        if override_config and not self._is_safe_systemd_content(override_config):
            raise ValueError("Invalid override config")

    def _is_safe_systemd_content(self, content: str) -> bool:
        """Check if systemd content is safe."""
        # Block dangerous patterns
        dangerous_patterns = [
            "ExecStartPre=/bin/rm",
            "ExecStart=/bin/rm",
            "ExecStart=rm ",
            "../",
            "/etc/passwd",
            "/etc/shadow",
            "sudo",
            "su ",
        ]

        content_lower = content.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in content_lower:
                return False

        return True
