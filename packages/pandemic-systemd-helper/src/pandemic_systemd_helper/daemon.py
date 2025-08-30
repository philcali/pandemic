"""Privileged systemd helper daemon."""

import asyncio
import logging
import os
import pwd
import signal
from pathlib import Path
from typing import Any, Dict

from pandemic_common.protocol import UDSProtocol

from .operations import SystemdOperations
from .validator import RequestValidator


class HelperDaemon:
    """Privileged systemd helper daemon."""

    def __init__(
        self,
        socket_path: str = "/var/run/pandemic/systemd-helper.sock",
        socket_mode: int = 660,
        socket_owner: str = "pandemic",
    ):
        self.socket_path = socket_path
        self.validator = RequestValidator()
        self.operations = SystemdOperations()
        self.server = None
        self.running = False
        self.socket_mode = socket_mode
        self.socket_owner = socket_owner
        self.logger = logging.getLogger(__name__)
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
        """Start the helper daemon."""
        if os.geteuid() != 0:
            raise RuntimeError("Helper daemon must run as root")

        self.logger.info("Starting privileged systemd helper")

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

            # Set socket permissions (readable/writable by pandemic group)
            user_info = pwd.getpwnam(self.socket_owner)
            os.chmod(socket_path, int(str(self.socket_mode), 8))
            os.chown(socket_path, user_info.pw_uid, user_info.pw_gid)

            self.running = True
            self.logger.info(f"Helper daemon listening on {socket_path}")

            # Start serving
            async with self.server:
                await self.server.serve_forever()

        except Exception as e:
            self.logger.error(f"Failed to start helper daemon: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop the helper daemon."""
        if not self.running:
            return

        self.logger.info("Stopping helper daemon")
        self.running = False

        try:
            if self.server:
                self.server.close()
                await self.server.wait_closed()

            # Clean up socket
            socket_path = Path(self.socket_path)
            if socket_path.exists():
                socket_path.unlink()

            self.logger.info("Helper daemon stopped")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection."""
        client_addr = writer.get_extra_info("peername", "unknown")
        self.logger.debug(f"Client connected: {client_addr}")

        try:
            while True:
                # Read request using UDS protocol
                request = await UDSProtocol.receive_message(reader)

                # Process request
                response = await self._process_request(request)

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
            except Exception as e:
                self.logger.warning(f"Error closing client connection: {e}")
                pass
            self.logger.debug(f"Client disconnected: {client_addr}")

    async def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process and execute validated request."""
        try:
            # Validate request
            self.validator.validate_request(request)

            command = request["command"]
            payload = request["payload"]

            # Log operation for audit
            self.logger.info(f"Executing {command} for {payload.get('serviceName', 'unknown')}")

            # Execute operation
            if command == "createService":
                result = await self.operations.create_service(
                    payload["serviceName"],
                    payload.get("templateContent", ""),
                    payload.get("overrideConfig", ""),
                )
            elif command == "removeService":
                result = await self.operations.remove_service(payload["serviceName"])
            elif command == "startService":
                result = await self.operations.start_service(payload["serviceName"])
            elif command == "stopService":
                result = await self.operations.stop_service(payload["serviceName"])
            elif command == "enableService":
                result = await self.operations.enable_service(payload["serviceName"])
            elif command == "disableService":
                result = await self.operations.disable_service(payload["serviceName"])
            elif command == "getStatus":
                result = await self.operations.get_status(payload["serviceName"])
            elif command == "getLogs":
                result = await self.operations.get_logs(
                    payload["serviceName"], payload.get("lines", 100)
                )
            else:
                raise ValueError(f"Unknown command: {command}")

            return result

        except Exception as e:
            self.logger.error(f"Request failed: {e}")
            return {"status": "error", "error": str(e)}
