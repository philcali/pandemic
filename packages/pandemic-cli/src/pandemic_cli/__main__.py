"""Main entry point for pandemic CLI."""

import sys

from .commands import cli


def main():
    """Main CLI entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        print("\nAborted!")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
