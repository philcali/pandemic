"""Tests for state management."""

import json

import pytest
from pandemic_core.state import StateManager


class TestStateManager:
    """Test state management."""

    def test_add_infection(self, state_manager):
        """Test adding infection to state."""
        infection_data = {"infectionId": "test-123", "name": "test-infection", "state": "running"}

        state_manager.add_infection("test-123", infection_data)

        retrieved = state_manager.get_infection("test-123")
        assert retrieved == infection_data
        assert state_manager.get_infection_count() == 1

    def test_remove_infection(self, state_manager):
        """Test removing infection from state."""
        infection_data = {"infectionId": "test-123", "name": "test"}

        state_manager.add_infection("test-123", infection_data)
        assert state_manager.get_infection_count() == 1

        removed = state_manager.remove_infection("test-123")
        assert removed is True
        assert state_manager.get_infection("test-123") is None
        assert state_manager.get_infection_count() == 0

    def test_remove_nonexistent_infection(self, state_manager):
        """Test removing non-existent infection."""
        removed = state_manager.remove_infection("nonexistent")
        assert removed is False

    def test_list_infections(self, state_manager):
        """Test listing all infections."""
        infections = [
            {"infectionId": "test-1", "name": "test1"},
            {"infectionId": "test-2", "name": "test2"},
        ]

        for i, infection in enumerate(infections):
            state_manager.add_infection(f"test-{i+1}", infection)

        all_infections = state_manager.list_infections()
        assert len(all_infections) == 2
        assert all_infections == infections

    def test_update_infection_state(self, state_manager):
        """Test updating infection state."""
        infection_data = {"infectionId": "test-123", "state": "stopped"}
        state_manager.add_infection("test-123", infection_data)

        state_manager.update_infection_state("test-123", "running")

        updated = state_manager.get_infection("test-123")
        assert updated["state"] == "running"

    def test_get_running_count(self, state_manager):
        """Test counting running infections."""
        infections = [
            {"infectionId": "test-1", "state": "running"},
            {"infectionId": "test-2", "state": "stopped"},
            {"infectionId": "test-3", "state": "running"},
        ]

        for i, infection in enumerate(infections):
            state_manager.add_infection(f"test-{i+1}", infection)

        assert state_manager.get_running_count() == 2
        assert state_manager.get_infection_count() == 3

    def test_state_persistence(self, test_config, temp_dir):
        """Test state persistence across manager instances."""
        # Create first manager and add infection
        manager1 = StateManager(test_config)
        infection_data = {"infectionId": "test-123", "name": "persistent"}
        manager1.add_infection("test-123", infection_data)

        # Create second manager (should load existing state)
        manager2 = StateManager(test_config)
        retrieved = manager2.get_infection("test-123")

        assert retrieved == infection_data
        assert manager2.get_infection_count() == 1
