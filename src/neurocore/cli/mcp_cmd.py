"""neurocore mcp — interact with MCP servers from the CLI.

These commands require the optional ``neurocore-skill-mcp`` package:

    pip install neurocore-skill-mcp

Usage:
    neurocore mcp list-tools --command docker --args "run,-i,--rm,server-image"
    neurocore mcp list-tools --url https://example.com/mcp
    neurocore mcp call <tool> --command ... --arg key=value
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console(stderr=True)
output_console = Console()

mcp_app = typer.Typer(
    name="mcp",
    help="Inspect and call MCP server tools (needs neurocore-skill-mcp).",
    no_args_is_help=True,
)


def _import_client() -> Any:
    try:
        from neurocore_skill_mcp import client
    except ImportError:
        console.print(
            "[red]MCP support is not installed.[/red] "
            "Run: pip install neurocore-skill-mcp"
        )
        raise typer.Exit(code=1) from None
    return client


def _build_cfg(
    command: Optional[str], args: str, url: Optional[str]
) -> dict[str, object]:
    if url:
        return {"transport": "http", "url": url}
    if command:
        arg_list = [a for a in args.split(",") if a] if args else []
        return {"transport": "stdio", "command": command, "args": arg_list}
    raise typer.BadParameter("Provide either --command (stdio) or --url (http).")


@mcp_app.command("list-tools")
def list_tools(
    command: Optional[str] = typer.Option(None, "--command", help="stdio executable."),
    args: str = typer.Option("", "--args", help="Comma-separated args for --command."),
    url: Optional[str] = typer.Option(None, "--url", help="streamable HTTP endpoint."),
) -> None:
    """List the tools a server exposes."""
    client = _import_client()
    cfg = _build_cfg(command, args, url)

    async def _run() -> list[Any]:
        async with client.open_session(cfg) as session:
            result = await session.list_tools()
            return list(result.tools)

    try:
        tools = asyncio.run(_run())
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Failed to list tools:[/red] {e}")
        raise typer.Exit(code=1) from None

    if not tools:
        console.print("[dim]No tools exposed.[/dim]")
        return
    table = Table(title="MCP tools")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    for tool in tools:
        table.add_row(tool.name, (getattr(tool, "description", "") or "")[:80])
    output_console.print(table)


@mcp_app.command("call")
def call_tool(
    tool: str = typer.Argument(help="Tool name to invoke."),
    arg: list[str] = typer.Option([], "--arg", help="Tool argument KEY=VALUE."),
    command: Optional[str] = typer.Option(None, "--command", help="stdio executable."),
    args: str = typer.Option("", "--args", help="Comma-separated args for --command."),
    url: Optional[str] = typer.Option(None, "--url", help="streamable HTTP endpoint."),
) -> None:
    """Call a single tool and print its result."""
    client = _import_client()
    cfg = _build_cfg(command, args, url)
    call_args: dict[str, str] = {}
    for item in arg:
        key, _, value = item.partition("=")
        call_args[key.strip()] = value

    async def _run() -> object:
        async with client.open_session(cfg) as session:
            response = await session.call_tool(tool, call_args)
            return client.normalize_content(response)

    try:
        result = asyncio.run(_run())
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Tool call failed:[/red] {e}")
        raise typer.Exit(code=1) from None
    typer.echo(json.dumps(result, indent=2, default=str))
