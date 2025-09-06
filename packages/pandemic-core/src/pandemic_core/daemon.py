"""Refactored core daemon with decoupled event bus."""

import uuid
from typing import Any, Dict, Optional

from pandemic_common import UnixDaemonServer, route

from .config import DaemonConfig
from .event_client import EventClient
from .sources import SourceManager
from .state import StateManager
from .systemd import SystemdManager


class PandemicDaemon(UnixDaemonServer):
    """Core pandemic daemon with decoupled event bus."""

    def __init__(self, config: DaemonConfig):
        super().__init__(
            config.socket_path,
            config.socket_mode,
            config.socket_owner,
            config.socket_group,
        )
        self.config = config
        self.state_manager = StateManager(config)
        self.systemd_manager = SystemdManager(config)
        self.source_manager = SourceManager(config)
        self.event_client: Optional[EventClient] = None
        self.subscriptions: Dict[str, Dict[str, str]] = {}

    async def on_startup(self):
        """Initialize event client if event bus available."""
        if self.config.event_bus_enabled:
            self.event_client = EventClient()
            # Try to connect and publish startup event
            await self._publish_event(
                "system.started",
                {"daemon": "pandemic-core", "version": "0.0.1", "socketPath": self.socket_path},
            )

    async def on_shutdown(self):
        """Publish shutdown event and disconnect from event bus."""
        if self.event_client:
            await self._publish_event("system.stopping", {"daemon": "pandemic-core"})
            await self.event_client.disconnect()

    async def _publish_event(self, event_type: str, payload: Dict[str, Any]):
        """Publish event via event client with graceful degradation."""
        if not self.event_client:
            return

        try:
            await self.event_client.publish("core", event_type, payload)
            self.logger.debug(f"Published event: {event_type}")
        except Exception as e:
            self.logger.debug(f"Event publishing failed (event bus unavailable): {e}")

    @route("health")
    async def handle_health(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check."""
        infection_id = payload.get("infectionId")

        if infection_id:
            infection = self.state_manager.get_infection(infection_id)
            if not infection:
                raise ValueError(f"Infection not found: {infection_id}")
            return {"status": "healthy", "infectionId": infection_id}
        else:
            health_data = {"status": "healthy", "daemon": True}

            # Add event bus health if available
            if self.event_client:
                try:
                    stats = await self.event_client.get_stats()
                    health_data["eventBus"] = stats
                except Exception:
                    health_data["eventBus"] = {"status": "unavailable"}

            return health_data

    @route("status")
    async def handle_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status request."""
        infection_id = payload.get("infectionId")

        if infection_id:
            infection = self.state_manager.get_infection(infection_id)
            if not infection:
                raise ValueError(f"Infection not found: {infection_id}")

            service_name = infection.get("serviceName")
            if service_name:
                systemd_status = await self.systemd_manager.get_service_status(service_name)
                infection["systemdStatus"] = systemd_status
                infection["state"] = self._map_systemd_state(systemd_status["activeState"])

            if infection_id in self.subscriptions:
                infection["eventSubscriptions"] = self.subscriptions[infection_id]

            return infection
        else:
            status_data = {
                "daemon": "running",
                "infections": len(self.state_manager.list_infections()),
                "uptime": "0h 0m",
            }

            if self.event_client:
                try:
                    stats = await self.event_client.get_stats()
                    status_data["eventBus"] = {
                        "enabled": True,
                        "sources": stats.get("totalSources", 0),
                        "subscriptions": len(self.subscriptions),
                    }
                except Exception:
                    status_data["eventBus"] = {"enabled": True, "status": "unavailable"}

            return status_data

    @route("list")
    async def handle_list(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

    @route("install")
    async def handle_install(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle infection installation."""
        source = payload.get("source")
        if not source:
            raise ValueError("Source is required for installation")

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

        self.state_manager.add_infection(infection_id, infection)

        await self._publish_event(
            "infection.installing", {"infectionId": infection_id, "name": name}
        )

        try:
            install_result = await self.source_manager.install_from_source(source, name)

            infection.update(
                {
                    "installationPath": install_result["installationPath"],
                    "downloadInfo": install_result["downloadInfo"],
                    "configInfo": install_result["configInfo"],
                }
            )

            service_name = await self.systemd_manager.create_service(infection_id, infection)
            infection["serviceName"] = service_name

            infection["state"] = "installed"
            self.state_manager.add_infection(infection_id, infection)

            # Create event source for infection
            if self.event_client:
                try:
                    await self.event_client.create_source(infection_id)
                except Exception as e:
                    self.logger.debug(f"Failed to create event source: {e}")

            await self._publish_event(
                "infection.installed", {"infectionId": infection_id, "name": name}
            )

            return {
                "infectionId": infection_id,
                "serviceName": service_name,
                "installationPath": install_result["installationPath"],
            }
        except Exception as e:
            infection["state"] = "failed"
            infection["error"] = str(e)
            self.state_manager.add_infection(infection_id, infection)

            await self._publish_event(
                "infection.failed", {"infectionId": infection_id, "error": str(e)}
            )
            raise

    @route("remove")
    async def handle_remove(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

        if service_name:
            await self.systemd_manager.remove_service(service_name)
            removed_services.append(service_name)

        if infection_id in self.subscriptions:
            del self.subscriptions[infection_id]

        if payload.get("cleanup", True):
            infection_path = f"{self.config.infections_dir}/{infection['name']}"
            removed_files.append(infection_path)

        self.state_manager.remove_infection(infection_id)

        await self._publish_event("infection.removed", {"infectionId": infection_id})

        return {"removedFiles": removed_files, "removedServices": removed_services}

    @route("start")
    async def handle_start(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

        await self._publish_event("infection.started", {"infectionId": infection_id})

        return {"status": "started", "infectionId": infection_id}

    @route("stop")
    async def handle_stop(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

        await self._publish_event("infection.stopped", {"infectionId": infection_id})

        return {"status": "stopped", "infectionId": infection_id}

    def _extract_name_from_source(self, source: str) -> str:
        """Extract infection name from source URL."""
        if source.startswith("github://"):
            parts = source.replace("github://", "").split("/")
            if len(parts) >= 2:
                return parts[1].split("@")[0]
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
