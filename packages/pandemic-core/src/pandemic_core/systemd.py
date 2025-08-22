"""Systemd integration for pandemic infections."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict

from .config import DaemonConfig
from .systemd_client import SystemdHelperClient


class SystemdManager:
    """Manages systemd services for infections."""

    def __init__(self, config: DaemonConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.helper_client = SystemdHelperClient()

    async def create_service(self, infection_id: str, infection_data: Dict[str, Any]) -> str:
        """Create systemd service for infection."""
        service_name = f"pandemic-infection@{infection_data['name']}.service"

        try:
            await self.helper_client.connect()

            # Generate template and override config
            template_content = self._generate_service_template()
            override_config = self._generate_override_config(infection_data)

            # Create service via helper
            await self.helper_client.create_service(
                service_name, template_content, override_config, infection_id
            )

            self.logger.info(f"Created systemd service: {service_name}")
            return service_name

        finally:
            await self.helper_client.disconnect()

    async def remove_service(self, service_name: str):
        """Remove systemd service."""
        try:
            await self.helper_client.connect()
            await self.helper_client.remove_service(service_name)
            self.logger.info(f"Removed systemd service: {service_name}")
        finally:
            await self.helper_client.disconnect()

    async def start_service(self, service_name: str):
        """Start systemd service."""
        try:
            await self.helper_client.connect()
            await self.helper_client.start_service(service_name)
            self.logger.info(f"Started service: {service_name}")
        finally:
            await self.helper_client.disconnect()

    async def stop_service(self, service_name: str):
        """Stop systemd service."""
        try:
            await self.helper_client.connect()
            await self.helper_client.stop_service(service_name)
            self.logger.info(f"Stopped service: {service_name}")
        finally:
            await self.helper_client.disconnect()

    async def restart_service(self, service_name: str):
        """Restart systemd service."""
        await self.stop_service(service_name)
        await self.start_service(service_name)
        self.logger.info(f"Restarted service: {service_name}")

    async def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get systemd service status."""
        try:
            await self.helper_client.connect()
            response = await self.helper_client.get_status(service_name)

            return {
                "activeState": response.get("activeState", "unknown"),
                "subState": response.get("subState", "unknown"),
                "pid": response.get("pid"),
                "memoryUsage": self._format_memory(response.get("memoryUsage", "0")),
                "cpuUsage": "0%",  # TODO: Calculate from helper response
                "uptime": "0s",  # TODO: Calculate uptime
            }

        except Exception as e:
            self.logger.error(f"Failed to get service status for {service_name}: {e}")
            return {
                "activeState": "unknown",
                "subState": "unknown",
                "pid": None,
                "memoryUsage": "0B",
                "cpuUsage": "0%",
                "uptime": "0s",
            }
        finally:
            await self.helper_client.disconnect()

    async def get_service_logs(self, service_name: str, lines: int = 100) -> list:
        """Get service logs from journald."""
        try:
            await self.helper_client.connect()
            response = await self.helper_client.get_logs(service_name, lines)

            logs = []
            for log_entry in response.get("logs", []):
                logs.append(
                    {
                        "timestamp": log_entry.get("timestamp", ""),
                        "level": self._map_syslog_level(log_entry.get("level", "6")),
                        "message": log_entry.get("message", ""),
                        "pid": "",
                    }
                )

            return logs

        except Exception as e:
            self.logger.error(f"Failed to get logs for {service_name}: {e}")
            return []
        finally:
            await self.helper_client.disconnect()

    def _generate_service_template(self) -> str:
        """Generate systemd service template content."""
        return """[Unit]
Description=Pandemic Infection: %i
After=pandemic-core.service
Requires=pandemic-core.service
PartOf=pandemic-core.service

[Service]
Type=simple
User=pandemic-%i
Group=pandemic
WorkingDirectory=/opt/pandemic/infections/%i
ExecStart=/opt/pandemic/infections/%i/bin/%i
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=pandemic.target
"""

    def _generate_override_config(self, infection_data: Dict[str, Any]) -> str:
        """Generate systemd override configuration."""
        config_lines = ["[Service]"]

        # Add environment variables
        env_vars = infection_data.get("environment", {})
        env_vars["PANDEMIC_SOCKET"] = self.config.socket_path

        for key, value in env_vars.items():
            config_lines.append(f'Environment="{key}={value}"')

        # Add resource limits
        resources = infection_data.get("resources", {})
        if "memoryLimit" in resources:
            config_lines.append(f"MemoryLimit={resources['memoryLimit']}")
        if "cpuQuota" in resources:
            config_lines.append(f"CPUQuota={resources['cpuQuota']}")

        return "\n".join(config_lines) + "\n"

    def _format_memory(self, memory_bytes: str) -> str:
        """Format memory usage."""
        try:
            bytes_val = int(memory_bytes)
            if bytes_val == 0:
                return "0B"

            for unit in ["B", "KB", "MB", "GB"]:
                if bytes_val < 1024:
                    return f"{bytes_val:.1f}{unit}"
                bytes_val = int(bytes_val / 1024)

            return f"{bytes_val:.1f}TB"
        except Exception as e:
            self.logger.error(f"Failed to format memory: {e}")
            return "0B"

    def _format_cpu(self, cpu_nsec: str) -> str:
        """Format CPU usage."""
        # TODO: Calculate actual CPU percentage
        return "0%"

    def _map_syslog_level(self, priority: str) -> str:
        """Map syslog priority to log level."""
        level_map = {
            "0": "EMERG",
            "1": "ALERT",
            "2": "CRIT",
            "3": "ERROR",
            "4": "WARN",
            "5": "NOTICE",
            "6": "INFO",
            "7": "DEBUG",
        }
        return level_map.get(priority, "INFO")
