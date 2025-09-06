"""Event bus daemon entry point."""

import asyncio
import logging
import os
import sys

from .daemon import EventDaemon


def main():
    """Main entry point for event bus daemon."""
    # Configure logging
    log_level = os.getenv("PANDEMIC_LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get configuration from environment
    socket_path = os.getenv("PANDEMIC_SOCKET_PATH", "/var/run/pandemic/event-bus.sock")
    events_dir = os.getenv("PANDEMIC_EVENTS_DIR", "/var/run/pandemic/events")

    # Create and run daemon
    daemon = EventDaemon(socket_path=socket_path, events_dir=events_dir)

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logging.info("Event bus daemon stopped by user")
    except Exception as e:
        logging.error(f"Event bus daemon failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
