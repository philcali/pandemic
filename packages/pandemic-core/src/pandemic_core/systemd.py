"""Systemd integration for pandemic infections."""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

from .config import DaemonConfig


class SystemdManager:
    """Manages systemd services for infections."""

    def __init__(self, config: DaemonConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.service_template_path = Path("/etc/systemd/system/pandemic-infection@.service")

    async def create_service(self, infection_id: str, infection_data: Dict[str, Any]) -> str:
        """Create systemd service for infection."""
        service_name = f"pandemic-infection@{infection_data['name']}.service"

        # Ensure service template exists
        await self._ensure_service_template()

        # Create systemd drop-in directory for infection-specific config
        drop_in_dir = Path(f"/etc/systemd/system/{service_name}.d")
        drop_in_dir.mkdir(parents=True, exist_ok=True)

        # Create override config
        override_config = self._generate_override_config(infection_data)
        override_file = drop_in_dir / "pandemic.conf"
        override_file.write_text(override_config)

        # Reload systemd
        await self._run_systemctl("daemon-reload")

        self.logger.info(f"Created systemd service: {service_name}")
        return service_name

    async def remove_service(self, service_name: str):
        """Remove systemd service."""
        # Stop and disable service
        await self.stop_service(service_name)
        await self._run_systemctl("disable", service_name)

        # Remove drop-in directory
        drop_in_dir = Path(f"/etc/systemd/system/{service_name}.d")
        if drop_in_dir.exists():
            import shutil

            shutil.rmtree(drop_in_dir)

        # Reload systemd
        await self._run_systemctl("daemon-reload")

        self.logger.info(f"Removed systemd service: {service_name}")

    async def start_service(self, service_name: str):
        """Start systemd service."""
        await self._run_systemctl("start", service_name)
        self.logger.info(f"Started service: {service_name}")

    async def stop_service(self, service_name: str):
        """Stop systemd service."""
        await self._run_systemctl("stop", service_name)
        self.logger.info(f"Stopped service: {service_name}")

    async def restart_service(self, service_name: str):
        """Restart systemd service."""
        await self._run_systemctl("restart", service_name)
        self.logger.info(f"Restarted service: {service_name}")

    async def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get systemd service status."""
        try:
            # Get service properties
            result = await self._run_systemctl(
                "show",
                service_name,
                "--property=ActiveState,SubState,MainPID,MemoryCurrent,CPUUsageNSec",
            )

            properties = {}
            for line in result.stdout.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    properties[key] = value

            # Get uptime if service is running
            uptime = "0s"
            if properties.get("ActiveState") == "active":
                uptime_result = await self._run_systemctl(
                    "show", service_name, "--property=ActiveEnterTimestamp"
                )
                # TODO: Calculate uptime from timestamp

            return {
                "activeState": properties.get("ActiveState", "unknown"),
                "subState": properties.get("SubState", "unknown"),
                "pid": int(properties.get("MainPID", 0)) or None,
                "memoryUsage": self._format_memory(properties.get("MemoryCurrent", "0")),
                "cpuUsage": self._format_cpu(properties.get("CPUUsageNSec", "0")),
                "uptime": uptime,
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

    async def get_service_logs(self, service_name: str, lines: int = 100) -> list:
        """Get service logs from journald."""
        try:
            result = await self._run_command(
                "journalctl", "-u", service_name, "-n", str(lines), "--output=json"
            )

            logs = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    import json

                    log_entry = json.loads(line)
                    logs.append(
                        {
                            "timestamp": log_entry.get("__REALTIME_TIMESTAMP", ""),
                            "level": self._map_syslog_level(log_entry.get("PRIORITY", "6")),
                            "message": log_entry.get("MESSAGE", ""),
                            "pid": log_entry.get("_PID", ""),
                        }
                    )

            return logs

        except Exception as e:
            self.logger.error(f"Failed to get logs for {service_name}: {e}")
            return []

    async def _ensure_service_template(self):
        """Ensure systemd service template exists."""
        if not self.service_template_path.exists():
            template_content = """[Unit]
Description=Pandemic Infection: %i
After=pandemic.service
Requires=pandemic.service
PartOf=pandemic.service

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
            self.service_template_path.parent.mkdir(parents=True, exist_ok=True)
            self.service_template_path.write_text(template_content)
            self.logger.info("Created systemd service template")

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

    async def _run_systemctl(self, *args) -> subprocess.CompletedProcess:
        """Run systemctl command."""
        return await self._run_command("systemctl", *args)

    async def _run_command(self, *args) -> subprocess.CompletedProcess:
        """Run command asynchronously."""
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        result = subprocess.CompletedProcess(
            args, process.returncode or 0, stdout.decode(), stderr.decode()
        )

        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, args, result.stdout, result.stderr
            )

        return result

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
