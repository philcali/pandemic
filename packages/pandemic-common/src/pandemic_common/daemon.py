"""Base Unix daemon server implementation."""

import asyncio
import grp
import logging
import os
import pwd
import signal
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .protocol import UDSProtocol
from .routing import RouteRegistry


class UnixDaemonServer:
    """Base class for Unix domain socket daemon servers."""

    def __init__(
        self,
        socket_path: str,
        socket_mode: int = 660,
        socket_owner: Optional[str] = None,
        socket_group: Optional[str] = None,
    ):
        self.socket_path = socket_path
        self.socket_mode = socket_mode
        self.socket_owner = socket_owner
        self.socket_group = socket_group
        self.server: Optional[asyncio.Server] = None
        self.running = False
        self.logger = logging.getLogger(self.__class__.__name__)
        self.route_registry = RouteRegistry()

        # Register routes from subclass
        self.route_registry.register_routes(self)

        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down")
            if self.running:
                asyncio.create_task(self.stop())

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    async def start(self):
        """Start the daemon server."""
        self.logger.info(f"Starting {self.__class__.__name__}")

        try:
            # Ensure socket directory exists
            socket_path = Path(self.socket_path)
            socket_path.parent.mkdir(parents=True, exist_ok=True)

            # Remove existing socket
            if socket_path.exists():
                socket_path.unlink()

            # Create Unix domain socket server
            self.server = await asyncio.start_unix_server(
                self._handle_client, path=str(socket_path)
            )

            # Set socket permissions
            self._set_socket_permissions()

            # Call subclass startup hook
            await self.on_startup()

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

        self.logger.info(f"Stopping {self.__class__.__name__}")
        self.running = False

        try:
            # Call subclass shutdown hook
            await self.on_shutdown()

            # Stop server
            if self.server:
                self.server.close()
                await self.server.wait_closed()

            # Clean up socket
            socket_path = Path(self.socket_path)
            if socket_path.exists():
                socket_path.unlink()

            self.logger.info("Daemon stopped successfully")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def _set_socket_permissions(self):
        """Set socket file permissions and ownership."""
        try:
            # Set file mode
            os.chmod(self.socket_path, int(str(self.socket_mode), 8))

            # Set ownership if specified
            uid = gid = -1

            if self.socket_owner:
                try:
                    user_info = pwd.getpwnam(self.socket_owner)
                    uid = user_info.pw_uid
                except KeyError:
                    self.logger.warning(f"User '{self.socket_owner}' not found")

            if self.socket_group:
                try:
                    group_info = grp.getgrnam(self.socket_group)
                    gid = group_info.gr_gid
                except KeyError:
                    self.logger.warning(f"Group '{self.socket_group}' not found")

            if uid != -1 or gid != -1:
                os.chown(self.socket_path, uid, gid)

        except Exception as e:
            self.logger.error(f"Failed to set socket permissions: {e}")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection."""
        client_addr = writer.get_extra_info("peername", "unknown")
        self.logger.debug(f"Client connected: {client_addr}")

        try:
            while True:
                # Receive message using UDS protocol
                message = await UDSProtocol.receive_message(reader)

                # Process message
                response = await self._process_message(message)

                # Send response using UDS protocol
                await UDSProtocol.send_message(writer, response)

        except asyncio.IncompleteReadError:
            pass  # Client disconnected
        except Exception as e:
            self.logger.error(f"Error handling client {client_addr}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as ie:
                self.logger.error(f"Error closing writer for {client_addr}: {ie}")
                pass
            self.logger.debug(f"Client disconnected: {client_addr}")

    async def _process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming message and route to handler."""
        message_id = message.get("id", str(uuid.uuid4()))
        command = message.get("command")
        payload = message.get("payload", {})

        try:
            if not command:
                return UDSProtocol.create_response(message_id, error="Command is required")

            # Get handler for command
            handler = self.route_registry.get_handler(command)
            if not handler:
                return UDSProtocol.create_response(message_id, error=f"Unknown command: {command}")

            # Validate payload if validator exists
            validator = self.route_registry.get_validator(command)
            if validator:
                validator(payload)

            # Execute handler
            result = await handler(payload)

            return UDSProtocol.create_response(message_id, payload=result)

        except Exception as e:
            self.logger.error(f"Error processing command {command}: {e}")
            return UDSProtocol.create_response(message_id, error=str(e))

    async def on_startup(self):
        """Override in subclass for startup logic."""
        pass

    async def on_shutdown(self):
        """Override in subclass for shutdown logic."""
        pass
