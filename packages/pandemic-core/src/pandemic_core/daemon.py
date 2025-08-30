"""Core pandemic daemon implementation."""

import asyncio
import json
import logging
import os
import signal
from pathlib import Path
from typing import Any, Dict

from .config import DaemonConfig
from .events import EventBusManager
from .handlers import MessageHandler
from .state import StateManager


class PandemicDaemon:
    """Core pandemic daemon that manages infections via Unix domain socket."""

    def __init__(self, config: DaemonConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.state_manager = StateManager(config)
        self.event_bus = (
            EventBusManager(
                config.events_dir,
                config.event_rate_limit,
                config.event_burst_size,
                config.socket_mode,
                config.socket_group,
            )
            if config.event_bus_enabled
            else None
        )
        self.message_handler = MessageHandler(config, self.state_manager, self.event_bus)
        self.server = None
        self.running = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            if self.running:
                asyncio.create_task(self.stop())

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    async def start(self):
        """Start the daemon server."""
        self.logger.info("Starting pandemic daemon")

        try:
            # Start event bus if enabled
            if self.event_bus:
                await self.event_bus.start()
                self.logger.info("Event bus started successfully")

            # Ensure socket directory exists
            socket_path = Path(self.config.socket_path)
            socket_path.parent.mkdir(parents=True, exist_ok=True)

            # Remove existing socket
            if socket_path.exists():
                socket_path.unlink()

            # Create Unix domain socket server
            self.server = await asyncio.start_unix_server(
                self._handle_client, path=str(socket_path)
            )

            # Set socket permissions
            os.chmod(socket_path, int(str(self.config.socket_mode), 8))

            # Publish daemon started event
            if self.event_bus:
                await self.event_bus.publish_event(
                    "core",
                    "system.started",
                    {"daemon": "pandemic-core", "version": "0.0.1", "socketPath": str(socket_path)},
                )

            self.running = True
            self.logger.info(f"Daemon listening on {socket_path}")

            # Start serving
            async with self.server:
                await self.server.serve_forever()

        except Exception as e:
            self.logger.error(f"Failed to start daemon: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop the daemon server."""
        if not self.running:
            return

        self.logger.info("Stopping pandemic daemon")
        self.running = False

        try:
            # Publish daemon stopping event
            if self.event_bus:
                await self.event_bus.publish_event(
                    "core", "system.stopping", {"daemon": "pandemic-core"}
                )

            # Stop server
            if self.server:
                self.server.close()
                await self.server.wait_closed()

            # Stop event bus
            if self.event_bus:
                await self.event_bus.stop()
                self.logger.info("Event bus stopped")

            # Clean up socket
            socket_path = Path(self.config.socket_path)
            if socket_path.exists():
                socket_path.unlink()

            self.logger.info("Daemon stopped successfully")

        except Exception as e:
            self.logger.error(f"Error during daemon shutdown: {e}")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection."""
        client_addr = writer.get_extra_info("peername", "unknown")
        self.logger.debug(f"Client connected: {client_addr}")

        try:
            while True:
                # Read message length (4 bytes)
                length_data = await reader.readexactly(4)
                if not length_data:
                    break

                message_length = int.from_bytes(length_data, "big")
                if message_length > 1024 * 1024:  # 1MB limit
                    self.logger.warning(
                        f"Message too large from {client_addr}: {message_length} bytes"
                    )
                    break

                # Read message data
                message_data = await reader.readexactly(message_length)
                message = json.loads(message_data.decode("utf-8"))

                # Process message
                response = await self.message_handler.handle_message(message)

                # Send response
                response_data = json.dumps(response).encode("utf-8")
                response_length = len(response_data).to_bytes(4, "big")

                writer.write(response_length + response_data)
                await writer.drain()

        except asyncio.IncompleteReadError:
            # Client disconnected
            pass
        except json.JSONDecodeError as e:
            self.logger.warning(f"Invalid JSON from {client_addr}: {e}")
        except Exception as e:
            self.logger.error(f"Error handling client {client_addr}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                self.logger.warning(f"Error closing client connection: {e}")
            self.logger.debug(f"Client disconnected: {client_addr}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform daemon health check."""
        health_status = {
            "status": "healthy" if self.running else "stopped",
            "daemon": "pandemic-core",
            "running": self.running,
            "eventBusEnabled": self.config.event_bus_enabled,
        }

        if self.event_bus:
            health_status["eventBus"] = self.event_bus.get_stats()

        if self.state_manager:
            infections = self.state_manager.list_infections()
            health_status["infections"] = {
                "total": len(infections),
                "running": len([i for i in infections if i.get("state") == "running"]),
            }

        return health_status
