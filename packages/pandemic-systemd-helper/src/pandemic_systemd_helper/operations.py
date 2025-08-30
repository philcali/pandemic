"""Systemd operations for privileged helper."""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict


class SystemdOperations:
    """Executes validated systemd operations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def create_service(
        self, service_name: str, template_content: str = "", override_config: str = ""
    ) -> Dict[str, Any]:
        """Create systemd service with template and override."""
        try:
            # Create template if provided
            if template_content:
                template_path = Path(f"/etc/systemd/system/{service_name}")
                template_path.write_text(template_content)
                self.logger.info(f"Created service template: {template_path}")

            # Create drop-in directory and override if provided
            if override_config:
                drop_in_dir = Path(f"/etc/systemd/system/{service_name}.d")
                drop_in_dir.mkdir(parents=True, exist_ok=True)

                override_file = drop_in_dir / "pandemic.conf"
                override_file.write_text(override_config)
                self.logger.info(f"Created override config: {override_file}")

            # Reload systemd
            await self._run_systemctl("daemon-reload")

            return {"status": "success", "operation": "created"}

        except Exception as e:
            self.logger.error(f"Failed to create service {service_name}: {e}")
            raise

    async def remove_service(self, service_name: str) -> Dict[str, Any]:
        """Remove systemd service and cleanup files."""
        try:
            # Stop and disable service first
            await self._run_systemctl("stop", service_name)
            await self._run_systemctl("disable", service_name)

            # Remove service file
            service_path = Path(f"/etc/systemd/system/{service_name}")
            if service_path.exists():
                service_path.unlink()

            # Remove drop-in directory
            drop_in_dir = Path(f"/etc/systemd/system/{service_name}.d")
            if drop_in_dir.exists():
                import shutil

                shutil.rmtree(drop_in_dir)

            # Reload systemd
            await self._run_systemctl("daemon-reload")

            return {"status": "success", "operation": "removed"}

        except Exception as e:
            self.logger.error(f"Failed to remove service {service_name}: {e}")
            raise

    async def start_service(self, service_name: str) -> Dict[str, Any]:
        """Start systemd service."""
        await self._run_systemctl("start", service_name)
        return {"status": "success", "operation": "started"}

    async def stop_service(self, service_name: str) -> Dict[str, Any]:
        """Stop systemd service."""
        await self._run_systemctl("stop", service_name)
        return {"status": "success", "operation": "stopped"}

    async def enable_service(self, service_name: str) -> Dict[str, Any]:
        """Enable systemd service."""
        await self._run_systemctl("enable", service_name)
        return {"status": "success", "operation": "enabled"}

    async def disable_service(self, service_name: str) -> Dict[str, Any]:
        """Disable systemd service."""
        await self._run_systemctl("disable", service_name)
        return {"status": "success", "operation": "disabled"}

    async def get_status(self, service_name: str) -> Dict[str, Any]:
        """Get systemd service status."""
        try:
            result = await self._run_systemctl(
                "show", service_name, "--property=ActiveState,SubState,MainPID,MemoryCurrent"
            )

            properties = {}
            for line in result.stdout.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    properties[key] = value

            return {
                "status": "success",
                "activeState": properties.get("ActiveState", "unknown"),
                "subState": properties.get("SubState", "unknown"),
                "pid": int(properties.get("MainPID", 0)) or None,
                "memoryUsage": properties.get("MemoryCurrent", "0"),
            }

        except Exception as e:
            self.logger.error(f"Failed to get status for {service_name}: {e}")
            raise

    async def get_logs(self, service_name: str, lines: int = 100) -> Dict[str, Any]:
        """Get service logs from journald."""
        try:
            result = await self._run_command(
                "journalctl", "-u", service_name, "-n", str(lines), "--output=json"
            )

            logs = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    log_entry = json.loads(line)
                    logs.append(
                        {
                            "timestamp": log_entry.get("__REALTIME_TIMESTAMP", ""),
                            "level": log_entry.get("PRIORITY", "6"),
                            "message": log_entry.get("MESSAGE", ""),
                        }
                    )

            return {"status": "success", "logs": logs}

        except Exception as e:
            self.logger.error(f"Failed to get logs for {service_name}: {e}")
            raise

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
