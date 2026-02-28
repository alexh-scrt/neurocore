"""neurocore skill — list and inspect discovered skills.

Usage:
    neurocore skill list
    neurocore skill info echo
    neurocore skill info neuroweave --project-root /path/to/project
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from neurocore.errors import NeuroCoreError

console = Console()

skill_app = typer.Typer(
    name="skill",
    help="Discover and inspect skills.",
    no_args_is_help=True,
)


def _discover(project_root: Path | None) -> tuple:
    """Discover skills and return (registry, config).

    Lazy import to keep CLI startup fast.
    """
    from neurocore.config.loader import load_config
    from neurocore.skills.loader import discover_skills

    config = load_config(project_root=project_root)
    registry = discover_skills(config)
    return registry, config


@skill_app.command("list")
def skill_list(
    project_root: Optional[Path] = typer.Option(
        None,
        "--project-root",
        "-p",
        help="Project root directory (auto-detected if not provided).",
    ),
) -> None:
    """List all discovered skills."""
    try:
        registry, config = _discover(project_root)
    except NeuroCoreError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None

    metas = registry.list_skill_metas()

    if not metas:
        console.print("[yellow]No skills discovered.[/yellow]")
        console.print(
            "[dim]Add skills to the skills/ directory or install "
            "via pip with entry points.[/dim]"
        )
        return

    table = Table(title="Discovered Skills")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Version", style="green")
    table.add_column("Description")
    table.add_column("Tags", style="dim")

    for meta in metas:
        tags = ", ".join(meta.tags) if meta.tags else ""
        table.add_row(meta.name, meta.version, meta.description, tags)

    console.print(table)
    console.print(f"\n[dim]{len(metas)} skill(s) found[/dim]")


@skill_app.command("info")
def skill_info(
    name: str = typer.Argument(help="Skill name to inspect."),
    project_root: Optional[Path] = typer.Option(
        None,
        "--project-root",
        "-p",
        help="Project root directory (auto-detected if not provided).",
    ),
) -> None:
    """Show detailed information about a skill."""
    try:
        registry, config = _discover(project_root)
    except NeuroCoreError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None

    skill_cls = registry.get(name)
    if skill_cls is None:
        available = ", ".join(registry.list_skills()) or "(none)"
        console.print(
            f"[red]Error:[/red] Skill '{name}' not found. "
            f"Available: {available}"
        )
        raise typer.Exit(code=1)

    meta = skill_cls.skill_meta

    console.print()
    console.print(f"[bold cyan]{meta.name}[/bold cyan]  v{meta.version}")

    if meta.description:
        console.print(f"  {meta.description}")
    if meta.author:
        console.print(f"  [dim]Author:[/dim] {meta.author}")

    console.print()

    if meta.tags:
        console.print(f"  [dim]Tags:[/dim]     {', '.join(meta.tags)}")
    if meta.provides:
        console.print(f"  [dim]Provides:[/dim] {', '.join(meta.provides)}")
    if meta.consumes:
        console.print(f"  [dim]Consumes:[/dim] {', '.join(meta.consumes)}")
    if meta.requires:
        console.print(f"  [dim]Requires:[/dim] {', '.join(meta.requires)}")

    if meta.config_schema:
        console.print()
        console.print("  [dim]Config schema:[/dim]")
        import json

        from rich.syntax import Syntax

        schema_json = json.dumps(meta.config_schema, indent=2)
        syntax = Syntax(schema_json, "json", theme="monokai", padding=1)
        console.print(syntax)

    # Health check
    console.print()
    try:
        instance = skill_cls()
        instance.init(config.get_skill_config(name))
        healthy = instance.health_check()
        status = "[green]healthy[/green]" if healthy else "[yellow]unhealthy[/yellow]"
    except Exception:
        status = "[red]error[/red]"
    console.print(f"  [dim]Health:[/dim]   {status}")
    console.print()
