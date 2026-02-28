"""neurocore validate — validate a blueprint without executing.

Checks that:
1. The YAML file parses correctly
2. The blueprint structure is valid
3. All referenced skills are discovered and registered

Usage:
    neurocore validate blueprints/agent.flow.yaml
    neurocore validate flow.yaml --project-root /path/to/project
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from neurocore.errors import BlueprintError, NeuroCoreError

console = Console()


def validate_blueprint_cmd(
    blueprint: Path = typer.Argument(
        help="Path to the blueprint YAML file to validate.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    project_root: Optional[Path] = typer.Option(
        None,
        "--project-root",
        "-p",
        help="Project root directory (auto-detected if not provided).",
    ),
) -> None:
    """Validate a blueprint without executing it."""
    # Lazy imports for fast CLI startup
    from neurocore.config.loader import load_config
    from neurocore.runtime.blueprint import load_blueprint, validate_blueprint
    from neurocore.skills.loader import discover_skills

    blueprint_path = blueprint.resolve()

    # Step 1: Parse the blueprint YAML
    console.print(f"[dim]Validating:[/dim] {blueprint_path}")
    console.print()

    try:
        bp = load_blueprint(blueprint_path)
    except BlueprintError as e:
        console.print(f"[red]Parse error:[/red] {e}")
        raise typer.Exit(code=1) from None

    console.print(f"  [green]✓[/green] YAML parsing OK")
    console.print(f"  [green]✓[/green] Blueprint structure valid")
    console.print(
        f"    Name: {bp.name}  |  "
        f"Components: {len(bp.components)}  |  "
        f"Flow: {bp.flow.type}"
    )

    # Step 2: Discover skills and validate references
    try:
        config = load_config(project_root=project_root)
        registry = discover_skills(config)
    except NeuroCoreError as e:
        console.print(f"\n[red]Discovery error:[/red] {e}")
        raise typer.Exit(code=1) from None

    errors = validate_blueprint(bp, registry)

    if errors:
        console.print(f"\n  [red]✗[/red] Skill validation failed:")
        for error in errors:
            console.print(f"    [red]•[/red] {error}")
        raise typer.Exit(code=1)

    console.print(f"  [green]✓[/green] All skill references resolved")
    console.print(f"\n[green]Blueprint is valid.[/green]")
