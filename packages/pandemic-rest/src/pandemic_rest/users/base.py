"""Abstract base class for user management providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class User:
    """User information from authentication provider."""

    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    roles: List[str] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []


@dataclass
class AuthResult:
    """Result of authentication attempt."""

    success: bool
    user: Optional[User] = None
    error: Optional[str] = None


class UserProvider(ABC):
    """Abstract base class for user authentication providers."""

    def __init__(self, config: dict):
        self.config = config
        self.role_mapping = config.get("role_mapping", {})

    @abstractmethod
    async def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate user with username and password."""
        pass

    @abstractmethod
    async def get_user(self, username: str) -> Optional[User]:
        """Get user information by username."""
        pass

    def map_roles(self, provider_roles: List[str]) -> List[str]:
        """Map provider-specific roles to pandemic scopes."""
        mapped_roles = []
        for role in provider_roles:
            if role in self.role_mapping:
                mapped_roles.append(self.role_mapping[role])
            else:
                mapped_roles.append(role)
        return mapped_roles
