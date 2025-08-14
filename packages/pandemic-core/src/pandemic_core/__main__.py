"""Main entry point for pandemic daemon."""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from .config import DaemonConfig
from .daemon import PandemicDaemon


def setup_logging(config: DaemonConfig):
    """Setup logging configuration."""
    level = getattr(logging, config.log_level.upper(), logging.INFO)

    if config.structured_logging:
        import datetime
        import json

        class StructuredFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_entry)

        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
    else:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

    logging.basicConfig(level=level, handlers=[handler])


async def run():
    """Main daemon entry point."""
    # Load configuration
    config_path = "/etc/pandemic/daemon.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    # Try file config first, fall back to environment
    if Path(config_path).exists():
        config = DaemonConfig.from_file(config_path)
    else:
        config = DaemonConfig.from_env()

    setup_logging(config)
    logger = logging.getLogger(__name__)

    # Create daemon
    daemon = PandemicDaemon(config)

    # Setup signal handlers
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(daemon.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        asyncio.get_event_loop().add_signal_handler(sig, signal_handler)

    try:
        # Write PID file
        pid_file = Path(config.pid_file)
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()))

        logger.info("Starting pandemic daemon")
        await daemon.start()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Daemon error: {e}")
        return 1
    finally:
        # Clean up PID file
        if pid_file.exists():
            pid_file.unlink()

    return 0


def main():
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
