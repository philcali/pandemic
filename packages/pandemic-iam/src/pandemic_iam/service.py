"""Pandemic IAM service runner for systemd integration."""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

import uvicorn
import yaml

from .manager import IAMManager
from .metadata_server import MetadataServer


class IAMService:
    """IAM service for running as systemd service."""

    def __init__(self, config_path: str = "/etc/pandemic/iam/config.yaml"):
        self.config_path = config_path
        self.manager = None
        self.metadata_server = None
        self.running = False
        self.logger = logging.getLogger(__name__)

    def load_config(self) -> dict:
        """Load configuration from file."""
        config_file = Path(self.config_path)

        if not config_file.exists():
            # Use default configuration
            return {
                "metadata_server": {"host": "169.254.169.254", "port": 80},
                "providers": {
                    "aws": {"enabled": False},
                    "azure": {"enabled": False},
                    "gcp": {"enabled": False},
                },
                "certificates": {
                    "base_path": "/etc/pandemic/certs",
                    "default_cert": "/etc/pandemic/certs/pandemic-iam.pem",
                    "default_key": "/etc/pandemic/certs/pandemic-iam.key",
                },
            }

        with open(config_file) as f:
            return yaml.safe_load(f)

    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            self.running = False

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    async def run(self):
        """Run the IAM metadata service."""
        self.setup_logging()
        self.setup_signal_handlers()

        self.logger.info("Starting Pandemic IAM metadata service...")

        try:
            # Load configuration
            config = self.load_config()

            # Initialize IAM manager
            self.manager = IAMManager(config)

            # Create metadata server
            self.metadata_server = MetadataServer(self.manager, config)

            # Get server configuration
            server_config = config.get("metadata_server", {})
            host = server_config.get("host", "169.254.169.254")
            port = server_config.get("port", 80)

            self.logger.info(f"Starting metadata server on {host}:{port}")

            # Start token cleanup task
            cleanup_task = asyncio.create_task(self.metadata_server.cleanup_expired_tokens())

            # Configure uvicorn
            uvicorn_config = uvicorn.Config(
                self.metadata_server.app, host=host, port=port, log_level="info", access_log=True
            )

            server = uvicorn.Server(uvicorn_config)

            # Run server
            await server.serve()

            # Cancel cleanup task
            cleanup_task.cancel()

        except Exception as e:
            self.logger.error(f"IAM service error: {e}")
            return 1

        self.logger.info("IAM service stopped")
        return 0


async def main():
    """Main entry point."""
    config_path = os.getenv("PANDEMIC_IAM_CONFIG", "/etc/pandemic/iam/config.yaml")
    service = IAMService(config_path)
    return await service.run()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
