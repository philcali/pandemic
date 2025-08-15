"""User management providers."""

from .base import AuthResult, User, UserProvider
from .local import LocalUserProvider

__all__ = ["AuthResult", "User", "UserProvider", "LocalUserProvider"]


def create_user_provider(config: dict) -> UserProvider:
    """Create user provider based on configuration."""
    provider_type = config.get("provider", "local")

    if provider_type == "local":
        return LocalUserProvider(config.get("local", {}))
    elif provider_type == "ldap":
        from .ldap import LDAPUserProvider

        return LDAPUserProvider(config.get("ldap", {}))
    elif provider_type == "oidc":
        from .oidc import OIDCUserProvider

        return OIDCUserProvider(config.get("oidc", {}))
    else:
        raise ValueError(f"Unknown user provider: {provider_type}")
