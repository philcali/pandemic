"""Pandemic event bus infection plugin."""

__version__ = "0.0.1"

from .daemon import EventDaemon

__all__ = ["EventDaemon"]
