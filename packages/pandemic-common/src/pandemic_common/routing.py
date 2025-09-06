"""Routing decorator for Unix daemon servers."""

import functools
from typing import Any, Callable, Dict, Optional


def route(command: str, *, validate: Optional[Callable] = None):
    """Decorator to register command handlers.

    Args:
        command: Command name to handle
        validate: Optional validation function for payload
    """

    def decorator(func: Callable):
        # Store routing metadata on the function
        func._route_command = command
        func._route_validate = validate

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class RouteRegistry:
    """Registry for route handlers."""

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.validators: Dict[str, Optional[Callable]] = {}

    def register_routes(self, instance: Any):
        """Register all @route decorated methods from an instance."""
        for attr_name in dir(instance):
            attr = getattr(instance, attr_name)
            if hasattr(attr, "_route_command"):
                command = attr._route_command
                self.handlers[command] = attr
                self.validators[command] = getattr(attr, "_route_validate", None)

    def get_handler(self, command: str) -> Optional[Callable]:
        """Get handler for command."""
        return self.handlers.get(command)

    def get_validator(self, command: str) -> Optional[Callable]:
        """Get validator for command."""
        return self.validators.get(command)

    def list_commands(self) -> list[str]:
        """List all registered commands."""
        return list(self.handlers.keys())
