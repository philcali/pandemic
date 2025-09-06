import uuid
from typing import Any, Dict

from pandemic_common import UnixDaemonServer, route

from .config import DaemonConfig
from .events import EventBusManager
from .sources import SourceManager
from .state import StateManager
from .systemd import SystemdManager


class PandemicDaemon(UnixDaemonServer):
    """Core pandemic daemon that manages infections via Unix domain socket."""

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
        self.subscriptions: Dict[str, Dict[str, str]] = {}  # infection_id -> {source: pattern}

    async def on_startup(self):
        """Start event bus if enabled."""
        if self.event_bus:
            await self.event_bus.start()
            self.logger.info("Event bus started successfully")

            # Publish daemon started event
            await self._publish_event(
                "system.started",
                {"daemon": "pandemic-core", "version": "0.0.1", "socketPath": self.socket_path},
            )

    async def on_shutdown(self):
        """Stop event bus and publish shutdown event."""
        if self.event_bus:
            await self._publish_event("system.stopping", {"daemon": "pandemic-core"})
            await self.event_bus.stop()
            self.logger.info("Event bus stopped")

    async def _publish_event(self, event_type: str, payload: Dict[str, Any]):
        """Publish event to event bus if available."""
        if self.event_bus:
            await self.event_bus.publish_event("core", event_type, payload)

    @route("health")
    async def handle_health(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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
            health_data = {"status": "healthy", "daemon": True}

            # Add event bus health if enabled
            if self.event_bus:
                health_data["eventBus"] = self.event_bus.get_stats()

            return health_data

    @route("status")
    async def handle_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

            # Add event subscription info
            if infection_id in self.subscriptions:
                infection["eventSubscriptions"] = self.subscriptions[infection_id]

            return infection
        else:
            status_data = {
                "daemon": "running",
                "infections": len(self.state_manager.list_infections()),
                "uptime": "0h 0m",  # TODO: Calculate actual uptime
            }

            # Add event bus status
            if self.event_bus:
                status_data["eventBus"] = {
                    "enabled": True,
                    "sources": len(self.event_bus.list_sources()),
                    "subscriptions": len(self.subscriptions),
                }

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

        # Publish started event
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

        # Publish stopped event
        await self._publish_event("infection.stopped", {"infectionId": infection_id})

        return {"status": "stopped", "infectionId": infection_id}

    @route("restart")
    async def handle_restart(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

    @route("logs")
    async def handle_logs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

    @route("metrics")
    async def handle_metrics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

    @route("subscribeEvents")
    async def handle_subscribe_events(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

        # Publish subscription event
        await self._publish_event(
            "system.subscription",
            {
                "infectionId": infection_id,
                "action": "subscribe",
                "subscriptionCount": len(subscriptions),
            },
        )

        self.logger.debug(
            f"Updated subscriptions for {infection_id}: {len(subscriptions)} subscriptions"
        )

        return {
            "status": "subscribed",
            "infectionId": infection_id,
            "subscriptionCount": len(subscriptions),
        }

    @route("unsubscribeEvents")
    async def handle_unsubscribe_events(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

        # Publish unsubscription event
        await self._publish_event(
            "system.subscription", {"infectionId": infection_id, "action": "unsubscribe"}
        )

        self.logger.debug(f"Removed subscriptions for {infection_id}")

        return {"status": "unsubscribed", "infectionId": infection_id}

    @route("getConfig")
    async def handle_get_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get configuration."""
        infection_id = payload.get("infectionId")

        if infection_id:
            # TODO: Get infection-specific config
            return {"config": {}}
        else:
            # Return daemon config
            config_dict = self.config.to_dict()

            # Add event bus stats if available
            if self.event_bus:
                config_dict["eventBus"]["stats"] = self.event_bus.get_stats()

            return {"config": config_dict}

    @route("setConfig")
    async def handle_set_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set configuration."""
        # TODO: Implement config updates
        return {"status": "updated"}

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
