"""CLI commands for pandemic administration."""

import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .client import PandemicClient

console = Console()


@click.group()
@click.option(
    "--socket",
    default="/var/run/pandemic.sock",
    help="Path to pandemic daemon socket",
    show_default=True,
)
@click.pass_context
def cli(ctx, socket):
    """Pandemic CLI for edge computing system administration."""
    ctx.ensure_object(dict)
    ctx.obj["socket"] = socket


@cli.command()
@click.pass_context
def health(ctx):
    """Check daemon health."""

    async def _health():
        client = PandemicClient(ctx.obj["socket"])
        try:
            await client.connect()
            response = await client.health_check()

            if response["status"] == "success":
                console.print("✅ Daemon is healthy", style="green")
            else:
                console.print(f"❌ Health check failed: {response.get('error')}", style="red")
        except Exception as e:
            console.print(f"❌ Failed to connect: {e}", style="red")
        finally:
            await client.disconnect()

    asyncio.run(_health())


@cli.command()
@click.option("--state", help="Filter by infection state")
@click.pass_context
def list(ctx, state):
    """List all infections."""

    async def _list():
        client = PandemicClient(ctx.obj["socket"])
        try:
            await client.connect()
            response = await client.list_infections(state)

            if response["status"] == "success":
                infections = response["payload"]["infections"]
                total = response["payload"]["totalCount"]
                running = response["payload"]["runningCount"]

                console.print(f"Total: {total}, Running: {running}")

                if infections:
                    table = Table()
                    table.add_column("ID", style="cyan")
                    table.add_column("Name", style="magenta")
                    table.add_column("State", style="green")
                    table.add_column("Version")
                    table.add_column("Memory")

                    for infection in infections:
                        state_style = "green" if infection.get("state") == "running" else "yellow"
                        table.add_row(
                            infection.get("infectionId", "")[:12] + "...",
                            infection.get("name", ""),
                            Text(infection.get("state", ""), style=state_style),
                            infection.get("version", ""),
                            infection.get("memoryUsage", ""),
                        )

                    console.print(table)
                else:
                    console.print("No infections found")
            else:
                console.print(f"❌ Failed: {response.get('error')}", style="red")
        except Exception as e:
            console.print(f"❌ Failed to connect: {e}", style="red")
        finally:
            await client.disconnect()

    asyncio.run(_list())


@cli.command()
@click.argument("source")
@click.option("--name", help="Custom infection name")
@click.pass_context
def install(ctx, source, name):
    """Install infection from source."""

    async def _install():
        client = PandemicClient(ctx.obj["socket"])
        try:
            await client.connect()
            response = await client.install_infection(source, name)

            if response["status"] == "success":
                payload = response["payload"]
                console.print(f"✅ Installed: {payload['infectionId']}", style="green")
                console.print(f"Service: {payload['serviceName']}")
                console.print(f"Path: {payload['installationPath']}")
            else:
                console.print(f"❌ Installation failed: {response.get('error')}", style="red")
        except Exception as e:
            console.print(f"❌ Failed to connect: {e}", style="red")
        finally:
            await client.disconnect()

    asyncio.run(_install())


@cli.command()
@click.argument("infection_id")
@click.option("--keep-files", is_flag=True, help="Keep infection files")
@click.pass_context
def remove(ctx, infection_id, keep_files):
    """Remove infection."""

    async def _remove():
        client = PandemicClient(ctx.obj["socket"])
        try:
            await client.connect()
            response = await client.remove_infection(infection_id, not keep_files)

            if response["status"] == "success":
                console.print(f"✅ Removed: {infection_id}", style="green")
            else:
                console.print(f"❌ Removal failed: {response.get('error')}", style="red")
        except Exception as e:
            console.print(f"❌ Failed to connect: {e}", style="red")
        finally:
            await client.disconnect()

    asyncio.run(_remove())


@cli.command()
@click.argument("infection_id")
@click.pass_context
def start(ctx, infection_id):
    """Start infection."""

    async def _start():
        client = PandemicClient(ctx.obj["socket"])
        try:
            await client.connect()
            response = await client.start_infection(infection_id)

            if response["status"] == "success":
                console.print(f"✅ Started: {infection_id}", style="green")
            else:
                console.print(f"❌ Start failed: {response.get('error')}", style="red")
        except Exception as e:
            console.print(f"❌ Failed to connect: {e}", style="red")
        finally:
            await client.disconnect()

    asyncio.run(_start())


@cli.command()
@click.argument("infection_id")
@click.pass_context
def stop(ctx, infection_id):
    """Stop infection."""

    async def _stop():
        client = PandemicClient(ctx.obj["socket"])
        try:
            await client.connect()
            response = await client.stop_infection(infection_id)

            if response["status"] == "success":
                console.print(f"✅ Stopped: {infection_id}", style="green")
            else:
                console.print(f"❌ Stop failed: {response.get('error')}", style="red")
        except Exception as e:
            console.print(f"❌ Failed to connect: {e}", style="red")
        finally:
            await client.disconnect()

    asyncio.run(_stop())


@cli.command()
@click.argument("infection_id", required=False)
@click.pass_context
def status(ctx, infection_id):
    """Get daemon or infection status."""

    async def _status():
        client = PandemicClient(ctx.obj["socket"])
        try:
            await client.connect()
            response = await client.get_status(infection_id)

            if response["status"] == "success":
                payload = response["payload"]

                if infection_id:
                    # Infection status
                    console.print(f"Infection: {payload.get('name', 'Unknown')}")
                    console.print(f"ID: {payload.get('infectionId', '')}")
                    console.print(f"State: {payload.get('state', '')}")
                    console.print(f"Source: {payload.get('source', '')}")

                    if "systemdStatus" in payload:
                        systemd = payload["systemdStatus"]
                        console.print(f"PID: {systemd.get('pid', 'N/A')}")
                        console.print(f"Memory: {systemd.get('memoryUsage', 'N/A')}")
                        console.print(f"CPU: {systemd.get('cpuUsage', 'N/A')}")
                        console.print(f"Uptime: {systemd.get('uptime', 'N/A')}")
                else:
                    # Daemon status
                    console.print(f"Daemon: {payload.get('daemon', 'Unknown')}")
                    console.print(f"Infections: {payload.get('infections', 0)}")
                    console.print(f"Uptime: {payload.get('uptime', 'N/A')}")
            else:
                console.print(f"❌ Status failed: {response.get('error')}", style="red")
        except Exception as e:
            console.print(f"❌ Failed to connect: {e}", style="red")
        finally:
            await client.disconnect()

    asyncio.run(_status())


@cli.command()
@click.argument("infection_id")
@click.option("--lines", default=100, help="Number of log lines to show")
@click.pass_context
def logs(ctx, infection_id, lines):
    """Show infection logs."""

    async def _logs():
        client = PandemicClient(ctx.obj["socket"])
        try:
            await client.connect()
            response = await client.get_logs(infection_id, lines)

            if response["status"] == "success":
                logs = response["payload"]["logs"]
                for log in logs:
                    timestamp = log.get("timestamp", "")
                    level = log.get("level", "INFO")
                    message = log.get("message", "")

                    level_style = {
                        "ERROR": "red",
                        "WARN": "yellow",
                        "INFO": "blue",
                        "DEBUG": "dim",
                    }.get(level, "white")

                    console.print(f"[{timestamp}] [{level}] {message}", style=level_style)
            else:
                console.print(f"❌ Logs failed: {response.get('error')}", style="red")
        except Exception as e:
            console.print(f"❌ Failed to connect: {e}", style="red")
        finally:
            await client.disconnect()

    asyncio.run(_logs())
