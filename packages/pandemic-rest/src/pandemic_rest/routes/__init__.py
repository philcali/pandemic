"""Route handlers for pandemic-rest API."""

from .auth import create_auth_router
from .health import create_health_router
from .infections import create_infections_router

__all__ = ["create_auth_router", "create_health_router", "create_infections_router"]
