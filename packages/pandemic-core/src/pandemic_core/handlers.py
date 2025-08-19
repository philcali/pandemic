"""Message handlers for pandemic daemon operations."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from .config import DaemonConfig
from .sources import SourceManager
from .state import StateManager
from .systemd import SystemdManager


class MessageHandler:
    """Handles incoming messages and routes to appropriate operations."""

    def __init__(self, config: DaemonConfig, state_manager: StateManager, event_bus=None):
        self.config = config
        self.state_manager = state_manager
        self.systemd_manager = SystemdManager(config)
        self.source_manager = SourceManager(config)
        self.event_bus = event_bus
        self.subscriptions: Dict[str, Dict[str, str]] = {}  # infection_id -> {source: pattern}
        self.logger = logging.getLogger(__name__)

    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming message and return response."""
        try:
            command = message.get("command")
            message_id = message.get("id", str(uuid.uuid4()))

            self.logger.debug(f"Handling command: {command} (id: {message_id})")

            # Route to appropriate handler
            handler_map = {
                "health": self._handle_health,
                "status": self._handle_status,
                "list": self._handle_list,
                "install": self._handle_install,
                "remove": self._handle_remove,
                "start": self._handle_start,
                "stop": self._handle_stop,
                "restart": self._handle_restart,
                "getConfig": self._handle_get_config,
                "setConfig": self._handle_set_config,
                "logs": self._handle_logs,
                "metrics": self._handle_metrics,
                "subscribeEvents": self._handle_subscribe_events,
                "unsubscribeEvents": self._handle_unsubscribe_events,
            }

            if not command:
                return self._error_response(message_id, "Command is required")

            handler = handler_map.get(command)
            if not handler:
                return self._error_response(message_id, f"Unknown command: {command}")

            result = await handler(message.get("payload", {}))

            return {
                "id": message_id,
                "type": "response",
                "status": "success",
                "payload": result,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return self._error_response(message.get("id", str(uuid.uuid4())), str(e))

    async def _publish_event(self, event_type: str, payload: Dict[str, Any]):
        """Publish event to event bus if available."""
        if self.event_bus:
            await self.event_bus.publish_event("core", event_type, payload)

    def _error_response(self, message_id: str, error: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            "id": message_id,
            "type": "response",
            "status": "error",
            "error": error,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    async def _handle_subscribe_events(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle event subscription request."""
        infection_id = payload.get("infectionId")
        subscriptions = payload.get("subscriptions", [])

        if not infection_id:
            raise ValueError("infectionId is required")

        # Validate infection exists
        infection = self.state_manager.get_infection(infection_id)
        if not infection:
            raise ValueError(f"Infection not found: {infection_id}")

        # Store subscriptions
        self.subscriptions[infection_id] = {}
        for sub in subscriptions:
            source = sub.get("source")
            pattern = sub.get("pattern")
            if source and pattern:
                self.subscriptions[infection_id][source] = pattern

        self.logger.debug(
            f"Updated subscriptions for {infection_id}: {len(subscriptions)} subscriptions"
        )

        return {
            "status": "subscribed",
            "infectionId": infection_id,
            "subscriptionCount": len(subscriptions),
        }

    async def _handle_unsubscribe_events(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle event unsubscription request."""
        infection_id = payload.get("infectionId")
        subscriptions = payload.get("subscriptions", [])

        if not infection_id:
            raise ValueError("infectionId is required")

        if infection_id in self.subscriptions:
            # Remove specific subscriptions
            for sub in subscriptions:
                source = sub.get("source")
                if source in self.subscriptions[infection_id]:
                    del self.subscriptions[infection_id][source]

            # Clean up if no subscriptions left
            if not self.subscriptions[infection_id]:
                del self.subscriptions[infection_id]

        self.logger.debug(f"Removed subscriptions for {infection_id}")

        return {"status": "unsubscribed", "infectionId": infection_id}

    async def _handle_health(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check."""
        infection_id = payload.get("infectionId")

        if infection_id:
            # Check specific infection health
            infection = self.state_manager.get_infection(infection_id)
            if not infection:
                raise ValueError(f"Infection not found: {infection_id}")
            return {"status": "healthy", "infectionId": infection_id}
        else:
            # Daemon health check
            return {"status": "healthy", "daemon": True}

    async def _handle_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status request."""
        infection_id = payload.get("infectionId")

        if infection_id:
            infection = self.state_manager.get_infection(infection_id)
            if not infection:
                raise ValueError(f"Infection not found: {infection_id}")

            # Get systemd status if service exists
            service_name = infection.get("serviceName")
            if service_name:
                systemd_status = await self.systemd_manager.get_service_status(service_name)
                infection["systemdStatus"] = systemd_status
                infection["state"] = self._map_systemd_state(systemd_status["activeState"])

            return infection
        else:
            return {
                "daemon": "running",
                "infections": len(self.state_manager.list_infections()),
                "uptime": "0h 0m",  # TODO: Calculate actual uptime
            }

    async def _handle_list(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list infections request."""
        infections = self.state_manager.list_infections()
        filter_state = payload.get("filter", {}).get("state")

        if filter_state:
            infections = [i for i in infections if i.get("state") == filter_state]

        return {
            "infections": infections,
            "totalCount": len(infections),
            "runningCount": len([i for i in infections if i.get("state") == "running"]),
        }

    async def _handle_install(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle infection installation."""
        source = payload.get("source")
        if not source:
            raise ValueError("Source is required for installation")

        # Generate infection details
        infection_id = f"infection-{str(uuid.uuid4())[:8]}"
        name = payload.get("name") or self._extract_name_from_source(source)

        infection = {
            "infectionId": infection_id,
            "source": source,
            "state": "installing",
            "name": name,
            "environment": payload.get("configOverrides", {}).get("environment", {}),
            "resources": payload.get("configOverrides", {}).get("resources", {}),
        }

        # Add to state as installing
        self.state_manager.add_infection(infection_id, infection)

        # Publish installing event
        await self._publish_event(
            "infection.installing", {"infectionId": infection_id, "name": name}
        )

        try:
            # Install from source
            install_result = await self.source_manager.install_from_source(source, name)

            # Update infection with install info
            infection.update(
                {
                    "installationPath": install_result["installationPath"],
                    "downloadInfo": install_result["downloadInfo"],
                    "configInfo": install_result["configInfo"],
                }
            )

            # Create systemd service
            service_name = await self.systemd_manager.create_service(infection_id, infection)
            infection["serviceName"] = service_name

            # Update state to installed
            infection["state"] = "installed"
            self.state_manager.add_infection(infection_id, infection)

            # Create event socket for infection
            if self.event_bus:
                await self.event_bus.create_event_socket(infection_id)

            # Publish installed event
            await self._publish_event(
                "infection.installed", {"infectionId": infection_id, "name": name}
            )

            return {
                "infectionId": infection_id,
                "serviceName": service_name,
                "installationPath": install_result["installationPath"],
            }
        except Exception as e:
            # Update state to failed
            infection["state"] = "failed"
            infection["error"] = str(e)
            self.state_manager.add_infection(infection_id, infection)

            # Publish failed event
            await self._publish_event(
                "infection.failed", {"infectionId": infection_id, "error": str(e)}
            )
            raise

    async def _handle_remove(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle infection removal."""
        infection_id = payload.get("infectionId")
        if not infection_id:
            raise ValueError("infectionId is required")

        infection = self.state_manager.get_infection(infection_id)
        if not infection:
            raise ValueError(f"Infection not found: {infection_id}")

        service_name = infection.get("serviceName")
        removed_files = []
        removed_services = []

        # Remove systemd service
        if service_name:
            await self.systemd_manager.remove_service(service_name)
            removed_services.append(service_name)

        # Remove event socket
        if self.event_bus:
            await self.event_bus.remove_event_socket(infection_id)

        # Remove subscriptions
        if infection_id in self.subscriptions:
            del self.subscriptions[infection_id]

        # Remove files if cleanup requested
        if payload.get("cleanup", True):
            infection_path = f"{self.config.infections_dir}/{infection['name']}"
            # TODO: Actually remove files
            removed_files.append(infection_path)

        # Remove from state
        self.state_manager.remove_infection(infection_id)

        # Publish removed event
        await self._publish_event("infection.removed", {"infectionId": infection_id})

        return {"removedFiles": removed_files, "removedServices": removed_services}

    async def _handle_start(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle infection start."""
        infection_id = payload.get("infectionId")
        if not infection_id:
            raise ValueError("infectionId is required")

        infection = self.state_manager.get_infection(infection_id)
        if not infection:
            raise ValueError(f"Infection not found: {infection_id}")

        service_name = infection.get("serviceName")
        if not service_name:
            raise ValueError(f"No service configured for infection: {infection_id}")

        await self.systemd_manager.start_service(service_name)
        self.state_manager.update_infection_state(infection_id, "running")

        # Publish started event
        await self._publish_event("infection.started", {"infectionId": infection_id})

        return {"status": "started", "infectionId": infection_id}

    async def _handle_stop(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle infection stop."""
        infection_id = payload.get("infectionId")
        if not infection_id:
            raise ValueError("infectionId is required")

        infection = self.state_manager.get_infection(infection_id)
        if not infection:
            raise ValueError(f"Infection not found: {infection_id}")

        service_name = infection.get("serviceName")
        if not service_name:
            raise ValueError(f"No service configured for infection: {infection_id}")

        await self.systemd_manager.stop_service(service_name)
        self.state_manager.update_infection_state(infection_id, "stopped")

        # Publish stopped event
        await self._publish_event("infection.stopped", {"infectionId": infection_id})

        return {"status": "stopped", "infectionId": infection_id}

    async def _handle_restart(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle infection restart."""
        infection_id = payload.get("infectionId")
        if not infection_id:
            raise ValueError("infectionId is required")

        infection = self.state_manager.get_infection(infection_id)
        if not infection:
            raise ValueError(f"Infection not found: {infection_id}")

        service_name = infection.get("serviceName")
        if not service_name:
            raise ValueError(f"No service configured for infection: {infection_id}")

        await self.systemd_manager.restart_service(service_name)
        self.state_manager.update_infection_state(infection_id, "running")

        # Publish restarted event
        await self._publish_event("infection.restarted", {"infectionId": infection_id})

        return {"status": "restarted", "infectionId": infection_id}

    async def _handle_get_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get configuration."""
        infection_id = payload.get("infectionId")

        if infection_id:
            # TODO: Get infection-specific config
            return {"config": {}}
        else:
            # Return daemon config
            return {
                "config": {
                    "socketPath": self.config.socket_path,
                    "infectionsDir": self.config.infections_dir,
                    "logLevel": self.config.log_level,
                    "eventBusEnabled": self.config.event_bus_enabled,
                    "eventsDir": self.config.events_dir,
                }
            }

    async def _handle_set_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set configuration."""
        # TODO: Implement config updates
        return {"status": "updated"}

    async def _handle_logs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle logs request."""
        infection_id = payload.get("infectionId")
        if not infection_id:
            raise ValueError("infectionId is required")

        infection = self.state_manager.get_infection(infection_id)
        if not infection:
            raise ValueError(f"Infection not found: {infection_id}")

        service_name = infection.get("serviceName")
        if not service_name:
            raise ValueError(f"No service configured for infection: {infection_id}")

        lines = payload.get("lines", 100)
        logs = await self.systemd_manager.get_service_logs(service_name, lines)

        return {"logs": logs, "totalLines": len(logs)}

    async def _handle_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle metrics request."""
        infection_id = payload.get("infectionId")

        if infection_id:
            infection = self.state_manager.get_infection(infection_id)
            if not infection:
                raise ValueError(f"Infection not found: {infection_id}")

            service_name = infection.get("serviceName")
            if service_name:
                status = await self.systemd_manager.get_service_status(service_name)
                return {
                    "metrics": {
                        "memory": status["memoryUsage"],
                        "cpu": status["cpuUsage"],
                        "uptime": status["uptime"],
                    }
                }

        return {"metrics": {}}

    def _extract_name_from_source(self, source: str) -> str:
        """Extract infection name from source URL."""
        # Simple extraction from github://user/repo format
        if source.startswith("github://"):
            parts = source.replace("github://", "").split("/")
            if len(parts) >= 2:
                return parts[1].split("@")[0]  # Remove version tag
        return "unknown"

    def _map_systemd_state(self, active_state: str) -> str:
        """Map systemd active state to infection state."""
        state_map = {
            "active": "running",
            "inactive": "stopped",
            "failed": "failed",
            "activating": "starting",
            "deactivating": "stopping",
        }
        return state_map.get(active_state, "unknown")
