"""neurocore run — execute a blueprint via FlowEngine.

Loads configuration, discovers skills, parses the blueprint, and
executes through FlowEngine. Outputs the final context data.

Usage:
    neurocore run blueprints/agent.flow.yaml
    neurocore run flow.yaml --data input=hello --data count=5
    neurocore run flow.yaml --stream
    neurocore run flow.yaml --project-root /path/to/project
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from neurocore.errors import BlueprintError, ExecutionError, NeuroCoreError

console = Console(stderr=True)
output_console = Console()


def _parse_data_args(data: list[str]) -> dict[str, str]:
    """Parse --data KEY=VALUE arguments into a dict.

    Args:
        data: List of KEY=VALUE strings.

    Returns:
        Dict mapping keys to values.

    Raises:
        typer.BadParameter: If a data argument is malformed.
    """
    result: dict[str, str] = {}
    for item in data:
        if "=" not in item:
            raise typer.BadParameter(
                f"Invalid data format: '{item}'. Use KEY=VALUE."
            )
        key, _, value = item.partition("=")
        key = key.strip()
        if not key:
            raise typer.BadParameter(
                f"Invalid data format: '{item}'. Key cannot be empty."
            )
        result[key] = value
    return result


def run_blueprint(
    blueprint: Path = typer.Argument(
        help="Path to the blueprint YAML file.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    data: list[str] = typer.Option(
        [],
        "--data",
        "-d",
        help="Initial context data as KEY=VALUE pairs.",
    ),
    stream: bool = typer.Option(
        False,
        "--stream",
        help="Stream execution events as JSONL.",
    ),
    project_root: Optional[Path] = typer.Option(
        None,
        "--project-root",
        "-p",
        help="Project root directory (auto-detected if not provided).",
    ),
    output_json: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output result as JSON.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed execution info.",
    ),
) -> None:
    """Execute a blueprint via FlowEngine."""
    # Lazy imports to keep CLI startup fast
    from neurocore.config.loader import load_config
    from neurocore.runtime.blueprint import load_blueprint
    from neurocore.runtime.executor import (
        execute_blueprint as exec_bp,
        execute_blueprint_stream,
        load_and_run,
    )
    from neurocore.skills.loader import discover_skills

    # Parse data arguments
    initial_data = _parse_data_args(data) if data else None

    blueprint_path = blueprint.resolve()

    if verbose:
        console.print(f"[dim]Blueprint:[/dim] {blueprint_path}")
        if project_root:
            console.print(f"[dim]Project root:[/dim] {project_root}")
        if initial_data:
            console.print(f"[dim]Initial data:[/dim] {initial_data}")
        console.print()

    try:
        if stream:
            # Stream mode: print JSONL events
            neurocore_config = load_config(project_root=project_root)
            registry = discover_skills(neurocore_config)
            bp = load_blueprint(blueprint_path)

            async def _stream() -> None:
                async for event in execute_blueprint_stream(
                    bp, registry, neurocore_config, initial_data
                ):
                    line = json.dumps(event.to_dict(), default=str)
                    sys.stdout.write(line + "\n")
                    sys.stdout.flush()

            asyncio.run(_stream())
        else:
            result = load_and_run(
                blueprint_path,
                project_root=project_root,
                initial_data=initial_data,
            )

            # Output results
            if output_json:
                output_console.print(result.to_json())
            else:
                data_dict = (
                    result.data.to_dict()
                    if hasattr(result.data, "to_dict")
                    else dict(result.data)
                )
                json_str = json.dumps(data_dict, indent=2, default=str)
                syntax = Syntax(json_str, "json", theme="monokai")
                output_console.print(
                    Panel(syntax, title="[green]Result[/green]", border_style="green")
                )
    except BlueprintError as e:
        console.print(f"[red]Blueprint error:[/red] {e}")
        raise typer.Exit(code=1) from None
    except ExecutionError as e:
        console.print(f"[red]Execution error:[/red] {e}")
        raise typer.Exit(code=1) from None
    except NeuroCoreError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None
