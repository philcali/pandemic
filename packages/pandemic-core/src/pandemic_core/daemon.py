"""Core pandemic daemon implementation."""

import asyncio
import json
import logging
import os
import socket
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .config import DaemonConfig
from .handlers import MessageHandler
from .state import StateManager


class PandemicDaemon:
    """Core pandemic daemon that manages infections via Unix domain socket."""

    def __init__(self, config: DaemonConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.state_manager = StateManager(config)
        self.message_handler = MessageHandler(config, self.state_manager)
        self.server = None
        self.running = False

    async def start(self):
        """Start the daemon server."""
        self.logger.info("Starting pandemic daemon")

        # Ensure socket directory exists
        socket_path = Path(self.config.socket_path)
        socket_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing socket
        if socket_path.exists():
            socket_path.unlink()

        # Create Unix domain socket server
        self.server = await asyncio.start_unix_server(self._handle_client, path=str(socket_path))

        # Set socket permissions
        os.chmod(socket_path, self.config.socket_mode)

        self.running = True
        self.logger.info(f"Daemon listening on {socket_path}")

        # Start serving
        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Stop the daemon server."""
        self.logger.info("Stopping pandemic daemon")
        self.running = False

        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Clean up socket
        socket_path = Path(self.config.socket_path)
        if socket_path.exists():
            socket_path.unlink()

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
        except Exception as e:
            self.logger.error(f"Error handling client {client_addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            self.logger.debug(f"Client disconnected: {client_addr}")
