"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml
from pandemic_core.config import DaemonConfig


class TestDaemonConfig:
    """Test daemon configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DaemonConfig()

        assert config.socket_path == "/var/run/pandemic/daemon.sock"
        assert config.socket_mode == 0o660
        assert config.log_level == "INFO"
        assert config.allowed_sources == []

    def test_from_file(self, temp_dir):
        """Test loading configuration from YAML file."""
        config_file = temp_dir / "daemon.yaml"
        config_data = {
            "daemon": {"socket_path": "/tmp/test.sock", "socket_mode": 0o644},
            "storage": {"infections_dir": "/tmp/infections"},
            "logging": {"level": "DEBUG"},
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = DaemonConfig.from_file(str(config_file))

        assert config.socket_path == "/tmp/test.sock"
        assert config.socket_mode == 0o644
        assert config.infections_dir == "/tmp/infections"
        assert config.log_level == "DEBUG"

    def test_from_file_nonexistent(self):
        """Test loading from non-existent file returns defaults."""
        config = DaemonConfig.from_file("/nonexistent/file.yaml")

        assert config.socket_path == "/var/run/pandemic/daemon.sock"
        assert config.log_level == "INFO"

    def test_from_env(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "PANDEMIC_SOCKET_PATH": "/tmp/env.sock",
            "PANDEMIC_LOG_LEVEL": "WARN",
            "PANDEMIC_INFECTIONS_DIR": "/tmp/env/infections",
        }

        # Temporarily set environment variables
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            config = DaemonConfig.from_env()

            assert config.socket_path == "/tmp/env.sock"
            assert config.log_level == "WARN"
            assert config.infections_dir == "/tmp/env/infections"
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
