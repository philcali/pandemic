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

    # Event bus configuration
    event_bus_enabled: bool = True
    events_dir: str = "/var/run/pandemic/events"
    event_rate_limit: int = 100
    event_burst_size: int = 200

    def __post_init__(self):
        if self.allowed_sources is None:
            self.allowed_sources = []

    @classmethod
    def from_file(cls, config_path: str) -> "DaemonConfig":
        """Load configuration from YAML file."""
        config_file = Path(config_path)

        if not config_file.exists():
            return cls()

        try:
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            raise ValueError(f"Failed to load config file {config_path}: {e}")

        daemon_config = data.get("daemon", {})
        storage_config = data.get("storage", {})
        security_config = data.get("security", {})
        logging_config = data.get("logging", {})
        event_config = data.get("eventBus", {})

        # Parse rate limit configuration
        rate_limit_config = event_config.get("rateLimit", {})

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
            event_bus_enabled=event_config.get("enabled", cls.event_bus_enabled),
            events_dir=event_config.get("eventsDir", cls.events_dir),
            event_rate_limit=rate_limit_config.get("maxEventsPerSecond", cls.event_rate_limit),
            event_burst_size=rate_limit_config.get("burstSize", cls.event_burst_size),
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
            event_bus_enabled=os.getenv("PANDEMIC_EVENT_BUS_ENABLED", "true").lower() == "true",
            events_dir=os.getenv("PANDEMIC_EVENTS_DIR", cls.events_dir),
            event_rate_limit=int(os.getenv("PANDEMIC_EVENT_RATE_LIMIT", str(cls.event_rate_limit))),
            event_burst_size=int(os.getenv("PANDEMIC_EVENT_BURST_SIZE", str(cls.event_burst_size))),
        )

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Validate paths
        for path_name, path_value in [
            ("socket_path", self.socket_path),
            ("pid_file", self.pid_file),
            ("infections_dir", self.infections_dir),
            ("config_dir", self.config_dir),
            ("state_dir", self.state_dir),
            ("events_dir", self.events_dir),
        ]:
            if not path_value:
                errors.append(f"{path_name} cannot be empty")
            elif not os.path.isabs(path_value):
                errors.append(f"{path_name} must be an absolute path: {path_value}")

        # Validate socket mode
        if not (0o000 <= self.socket_mode <= 0o777):
            errors.append(f"Invalid socket_mode: {oct(self.socket_mode)}")

        # Validate rate limiting
        if self.event_rate_limit <= 0:
            errors.append(f"event_rate_limit must be positive: {self.event_rate_limit}")

        if self.event_burst_size <= 0:
            errors.append(f"event_burst_size must be positive: {self.event_burst_size}")

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"Invalid log_level: {self.log_level}")

        return errors

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "daemon": {
                "socket_path": self.socket_path,
                "socket_mode": oct(self.socket_mode),
                "socket_group": self.socket_group,
                "pid_file": self.pid_file,
            },
            "storage": {
                "infections_dir": self.infections_dir,
                "config_dir": self.config_dir,
                "state_dir": self.state_dir,
            },
            "security": {
                "validate_signatures": self.validate_signatures,
                "allowed_sources": self.allowed_sources,
            },
            "logging": {
                "level": self.log_level,
                "structured": self.structured_logging,
            },
            "eventBus": {
                "enabled": self.event_bus_enabled,
                "eventsDir": self.events_dir,
                "rateLimit": {
                    "maxEventsPerSecond": self.event_rate_limit,
                    "burstSize": self.event_burst_size,
                },
            },
        }
