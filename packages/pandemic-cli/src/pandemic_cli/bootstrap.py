"""Bootstrap manager for pandemic-core daemon setup."""

import os
import subprocess
from pathlib import Path
from typing import Dict, List


class BootstrapManager:
    """Manages pandemic-core daemon bootstrap process."""

    def __init__(self, user: str = "pandemic", socket_path: str = "/var/run/pandemic/daemon.sock"):
        self.user = user
        self.socket_path = socket_path
        self.service_name = "pandemic-core.service"
        self.service_path = Path(f"/etc/systemd/system/{self.service_name}")

    def bootstrap(self, dry_run: bool = False, force: bool = False) -> List[str]:
        """Execute bootstrap process."""
        actions = []

        if not dry_run:
            self._validate_requirements()
        actions.append("✓ Validated system requirements")

        if not dry_run:
            self._create_user()
        actions.append(f"✓ Created system user '{self.user}'")

        if not dry_run:
            self._setup_directories()
        actions.append("✓ Set up directories")

        if not dry_run:
            self._create_service_file(force)
        actions.append("✓ Generated systemd service")

        if not dry_run:
            self._enable_service()
        actions.append(f"✓ Enabled {self.service_name}")

        if not dry_run:
            self._start_service()
        actions.append(f"✓ Started {self.service_name}")

        if not dry_run:
            self._validate_startup()
        actions.append("✓ Validated daemon startup")

        return actions

    def _validate_requirements(self):
        """Validate system requirements."""
        if os.geteuid() != 0:
            raise RuntimeError("Bootstrap requires root privileges")

        subprocess.run(["systemctl", "--version"], check=True, capture_output=True)

    def _create_user(self):
        """Create system user if not exists."""
        try:
            subprocess.run(["id", self.user], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(
                ["useradd", "--system", "--no-create-home", "--shell", "/bin/false", self.user],
                check=True,
            )

    def _setup_directories(self):
        """Create required directories with proper permissions."""
        dirs = [Path(self.socket_path).parent, Path("/var/lib/pandemic"), Path("/var/log/pandemic")]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            subprocess.run(["chown", f"{self.user}:{self.user}", str(dir_path)], check=True)

    def _create_service_file(self, force: bool):
        """Create systemd service file."""
        if self.service_path.exists() and not force:
            return

        service_content = f"""[Unit]
Description=Pandemic Core Daemon
After=network.target
Wants=network.target

[Service]
Type=simple
User={self.user}
Group={self.user}
ExecStart=/usr/local/bin/pandemic
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
        self.service_path.write_text(service_content)

    def _enable_service(self):
        """Enable systemd service."""
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", self.service_name], check=True)

    def _start_service(self):
        """Start systemd service."""
        subprocess.run(["systemctl", "start", self.service_name], check=True)

    def _validate_startup(self):
        """Validate daemon started successfully."""
        result = subprocess.run(
            ["systemctl", "is-active", self.service_name], capture_output=True, text=True
        )
        if result.stdout.strip() != "active":
            raise RuntimeError("Service failed to start")
