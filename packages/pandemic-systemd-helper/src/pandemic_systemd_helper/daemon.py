import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from pandemic_common import UnixDaemonServer, route

from .validator import RequestValidator


class HelperDaemon(UnixDaemonServer):
    """Privileged systemd helper daemon with integrated operations."""

    def __init__(
        self,
        socket_path: str = "/var/run/pandemic/systemd-helper.sock",
        socket_mode: int = 660,
        socket_owner: str = "pandemic",
    ):
        super().__init__(socket_path, socket_mode, socket_owner, socket_owner)
        self.validator = RequestValidator()

    async def on_startup(self):
        """Startup validation."""
        if os.geteuid() != 0:
            raise RuntimeError("Helper daemon must run as root")

    @route("createService")
    async def create_service(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create systemd service with template and override."""
        self.validator.validate_request({"command": "createService", "payload": payload})

        service_name = payload["serviceName"]
        template_content = payload.get("templateContent", "")
        override_config = payload.get("overrideConfig", "")

        self.logger.info(f"Creating service: {service_name}")

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

    @route("removeService")
    async def remove_service(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Remove systemd service and cleanup files."""
        service_name = payload["serviceName"]
        self.logger.info(f"Removing service: {service_name}")

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

    @route("startService")
    async def start_service(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Start systemd service."""
        service_name = payload["serviceName"]
        await self._run_systemctl("start", service_name)
        return {"status": "success", "operation": "started"}

    @route("stopService")
    async def stop_service(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Stop systemd service."""
        service_name = payload["serviceName"]
        await self._run_systemctl("stop", service_name)
        return {"status": "success", "operation": "stopped"}

    @route("enableService")
    async def enable_service(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Enable systemd service."""
        service_name = payload["serviceName"]
        await self._run_systemctl("enable", service_name)
        return {"status": "success", "operation": "enabled"}

    @route("disableService")
    async def disable_service(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Disable systemd service."""
        service_name = payload["serviceName"]
        await self._run_systemctl("disable", service_name)
        return {"status": "success", "operation": "disabled"}

    @route("getStatus")
    async def get_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get systemd service status."""
        service_name = payload["serviceName"]

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

    @route("getLogs")
    async def get_logs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get service logs from journald."""
        service_name = payload["serviceName"]
        lines = payload.get("lines", 100)

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
