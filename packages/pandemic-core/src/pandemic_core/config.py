"""Configuration management for pandemic daemon."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class DaemonConfig:
    """Daemon configuration."""

    socket_path: str = "/var/run/pandemic.sock"
    socket_mode: int = 0o660
    socket_group: str = "pandemic"
    pid_file: str = "/var/run/pandemic.pid"
    infections_dir: str = "/opt/pandemic/infections"
    config_dir: str = "/etc/pandemic"
    state_dir: str = "/var/lib/pandemic"
    validate_signatures: bool = True
    allowed_sources: Optional[List[str]] = None
    log_level: str = "INFO"
    structured_logging: bool = True

    def __post_init__(self):
        if self.allowed_sources is None:
            self.allowed_sources = []

    @classmethod
    def from_file(cls, config_path: str) -> "DaemonConfig":
        """Load configuration from YAML file."""
        config_file = Path(config_path)

        if not config_file.exists():
            return cls()

        with open(config_file) as f:
            data = yaml.safe_load(f) or {}

        daemon_config = data.get("daemon", {})
        storage_config = data.get("storage", {})
        security_config = data.get("security", {})
        logging_config = data.get("logging", {})

        return cls(
            socket_path=daemon_config.get("socket_path", cls.socket_path),
            socket_mode=daemon_config.get("socket_mode", cls.socket_mode),
            socket_group=daemon_config.get("socket_group", cls.socket_group),
            pid_file=daemon_config.get("pid_file", cls.pid_file),
            infections_dir=storage_config.get("infections_dir", cls.infections_dir),
            config_dir=storage_config.get("config_dir", cls.config_dir),
            state_dir=storage_config.get("state_dir", cls.state_dir),
            validate_signatures=security_config.get("validate_signatures", cls.validate_signatures),
            allowed_sources=security_config.get("allowed_sources", cls.allowed_sources),
            log_level=logging_config.get("level", cls.log_level),
            structured_logging=logging_config.get("structured", cls.structured_logging),
        )

    @classmethod
    def from_env(cls) -> "DaemonConfig":
        """Load configuration from environment variables."""
        return cls(
            socket_path=os.getenv("PANDEMIC_SOCKET_PATH", cls.socket_path),
            socket_mode=int(os.getenv("PANDEMIC_SOCKET_MODE", str(cls.socket_mode)), 8),
            socket_group=os.getenv("PANDEMIC_SOCKET_GROUP", cls.socket_group),
            pid_file=os.getenv("PANDEMIC_PID_FILE", cls.pid_file),
            infections_dir=os.getenv("PANDEMIC_INFECTIONS_DIR", cls.infections_dir),
            config_dir=os.getenv("PANDEMIC_CONFIG_DIR", cls.config_dir),
            state_dir=os.getenv("PANDEMIC_STATE_DIR", cls.state_dir),
            log_level=os.getenv("PANDEMIC_LOG_LEVEL", cls.log_level),
        )
