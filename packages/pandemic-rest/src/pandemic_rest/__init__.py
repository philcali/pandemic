"""Pandemic REST - HTTP API plugin for Pandemic edge computing system."""

__version__ = "0.0.1"

from .app import create_app

__all__ = ["create_app"]
