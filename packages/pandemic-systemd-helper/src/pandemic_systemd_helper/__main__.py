"""Main entry point for privileged systemd helper."""

import argparse
import asyncio
import logging
import sys

from .daemon import HelperDaemon


def create_parser():
    parser = argparse.ArgumentParser(description="Pandemic Systemd Helper")
    parser.add_argument(
        "--socket-path",
        default="/var/run/pandemic/systemd-helper.sock",
        help="Path to the systemd helper socket",
    )
    parser.add_argument(
        "--socket-mode",
        type=int,
        default=432,
        help="Permissions for the systemd helper socket",
    )
    parser.add_argument(
        "--socket-owner",
        default="pandemic",
        help="Owner of the systemd helper socket",
    )
    return parser


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    parser = create_parser()
    args = parser.parse_args(sys.argv[1:])

    daemon = HelperDaemon(
        socket_mode=args.socket_mode, socket_owner=args.socket_owner, socket_path=args.socket_path
    )

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logging.info("Received interrupt, shutting down")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
