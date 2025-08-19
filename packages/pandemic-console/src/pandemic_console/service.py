"""Pandemic Console service runner for systemd integration."""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

import uvicorn
import yaml

from .app import create_app


class ConsoleService:
    """Console service for running as systemd service."""

    def __init__(self, config_path: str = "/etc/pandemic/console/config.yaml"):
        self.config_path = config_path
        self.running = False
        self.logger = logging.getLogger(__name__)

    def load_config(self) -> dict:
        """Load configuration from file."""
        config_file = Path(self.config_path)

        if not config_file.exists():
            # Return default configuration
            return {
                "server": {"host": "localhost", "port": 3000},
                "api": {"base_url": "https://localhost:8443/api/v1"},
                "logging": {"level": "INFO"},
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
        """Run the console service."""
        self.setup_logging()
        self.setup_signal_handlers()

        self.logger.info("Starting Pandemic Console service...")

        try:
            # Load configuration
            config = self.load_config()

            # Create FastAPI app
            app = create_app(config)

            # Get server configuration
            server_config = config.get("server", {})
            host = server_config.get("host", "localhost")
            port = server_config.get("port", 3000)

            self.logger.info(f"Starting console server on {host}:{port}")

            # Configure uvicorn
            uvicorn_config = uvicorn.Config(
                app, host=host, port=port, log_level="info", access_log=True
            )

            server = uvicorn.Server(uvicorn_config)

            # Run server
            await server.serve()

        except Exception as e:
            self.logger.error(f"Console service error: {e}")
            return 1

        self.logger.info("Console service stopped")
        return 0


async def main():
    """Main entry point."""
    config_path = os.getenv("PANDEMIC_CONSOLE_CONFIG", "/etc/pandemic/console/config.yaml")
    service = ConsoleService(config_path)
    return await service.run()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
