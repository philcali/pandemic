"""State management for pandemic daemon."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import DaemonConfig


class StateManager:
    """Manages daemon and infection state."""

    def __init__(self, config: DaemonConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.state_file = Path(config.state_dir) / "state.json"
        self._infections: Dict[str, Dict[str, Any]] = {}
        self._load_state()

    def _load_state(self):
        """Load state from disk."""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    data = json.load(f)
                    self._infections = data.get("infections", {})
                self.logger.info(f"Loaded state with {len(self._infections)} infections")
            else:
                self.logger.info("No existing state file, starting fresh")
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            self._infections = {}

    def _save_state(self):
        """Save state to disk."""
        try:
            # Ensure state directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state_data = {"infections": self._infections}

            # Write to temporary file first, then rename for atomicity
            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(state_data, f, indent=2)

            temp_file.rename(self.state_file)
            self.logger.debug("State saved successfully")

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def add_infection(self, infection_id: str, infection_data: Dict[str, Any]):
        """Add or update infection."""
        self._infections[infection_id] = infection_data
        self._save_state()
        self.logger.info(f"Added infection: {infection_id}")

    def remove_infection(self, infection_id: str) -> bool:
        """Remove infection."""
        if infection_id in self._infections:
            del self._infections[infection_id]
            self._save_state()
            self.logger.info(f"Removed infection: {infection_id}")
            return True
        return False

    def get_infection(self, infection_id: str) -> Optional[Dict[str, Any]]:
        """Get infection by ID."""
        return self._infections.get(infection_id)

    def list_infections(self) -> List[Dict[str, Any]]:
        """List all infections."""
        return list(self._infections.values())

    def update_infection_state(self, infection_id: str, state: str):
        """Update infection state."""
        if infection_id in self._infections:
            self._infections[infection_id]["state"] = state
            self._save_state()
            self.logger.debug(f"Updated infection {infection_id} state to {state}")

    def get_infection_count(self) -> int:
        """Get total infection count."""
        return len(self._infections)

    def get_running_count(self) -> int:
        """Get count of running infections."""
        return len([i for i in self._infections.values() if i.get("state") == "running"])
