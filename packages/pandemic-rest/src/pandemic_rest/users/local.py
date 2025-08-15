"""Local file-based user provider for development."""

import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional

import yaml

from .base import AuthResult, User, UserProvider


class LocalUserProvider(UserProvider):
    """Local file-based user provider."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.users_file = Path(config.get("users_file", "/etc/pandemic/users.yaml"))
        self.users_cache: Dict[str, dict] = {}
        self.logger = logging.getLogger(__name__)
        self._load_users()

    def _load_users(self):
        """Load users from YAML file."""
        if not self.users_file.exists():
            self.logger.warning(f"Users file not found: {self.users_file}")
            return

        try:
            with open(self.users_file) as f:
                data = yaml.safe_load(f)
                self.users_cache = data.get("users", {})
                self.logger.info(f"Loaded {len(self.users_cache)} users from {self.users_file}")
        except Exception as e:
            self.logger.error(f"Failed to load users file: {e}")

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()

    async def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate user against local users file."""
        if username not in self.users_cache:
            return AuthResult(success=False, error="User not found")

        user_data = self.users_cache[username]
        stored_hash = user_data.get("password_hash")

        if not stored_hash:
            return AuthResult(success=False, error="No password configured")

        # Check password
        password_hash = self._hash_password(password)
        if password_hash != stored_hash:
            return AuthResult(success=False, error="Invalid password")

        # Create user object
        user = User(
            username=username,
            email=user_data.get("email"),
            full_name=user_data.get("full_name"),
            roles=self.map_roles(user_data.get("roles", [])),
        )

        return AuthResult(success=True, user=user)

    async def get_user(self, username: str) -> Optional[User]:
        """Get user information by username."""
        if username not in self.users_cache:
            return None

        user_data = self.users_cache[username]
        return User(
            username=username,
            email=user_data.get("email"),
            full_name=user_data.get("full_name"),
            roles=self.map_roles(user_data.get("roles", [])),
        )
