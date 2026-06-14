"""neurocore new — scaffold a project from a template.

Usage:
    neurocore new --list
    neurocore new ollama-agent my-agent
    neurocore new research-agent ac1-researcher --dir ~/projects
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from neurocore.scaffold.registry import TEMPLATES, get_template, list_templates
from neurocore.scaffold.render import TEMPLATES_DIR, render_tree

console = Console()


def _print_templates() -> None:
    table = Table(title="Available templates")
    table.add_column("Template", style="cyan")
    table.add_column("Description")
    table.add_column("Suggested skills", style="dim")
    for spec in list_templates():
        table.add_row(spec.name, spec.description, ", ".join(spec.suggested_skills))
    console.print(table)


def new_project(
    template: Optional[str] = typer.Argument(
        None, help="Template name (run 'neurocore new --list' to see options)."
    ),
    name: Optional[str] = typer.Argument(None, help="Project name."),
    directory: Path = typer.Option(
        Path("."), "--dir", "-d", help="Parent directory to create the project in."
    ),
    list_flag: bool = typer.Option(
        False, "--list", "-l", help="List available templates and exit."
    ),
) -> None:
    """Scaffold a new NeuroCore project from a template."""
    if list_flag or template is None:
        _print_templates()
        if list_flag:
            return
        console.print("\n[dim]Usage:[/dim] neurocore new <template> <name>")
        raise typer.Exit(code=0 if list_flag else 1)

    spec = get_template(template)
    if spec is None:
        console.print(f"[red]Unknown template:[/red] '{template}'\n")
        _print_templates()
        raise typer.Exit(code=1)

    if not name:
        console.print("[red]Error:[/red] a project name is required.")
        raise typer.Exit(code=1)

    project_dir = directory.resolve() / name
    if project_dir.exists():
        console.print(f"[red]Error:[/red] Directory '{project_dir}' already exists.")
        raise typer.Exit(code=1)

    src = TEMPLATES_DIR / spec.dir_name
    if not src.is_dir():
        console.print(f"[red]Error:[/red] template files missing for '{template}'.")
        raise typer.Exit(code=1)

    try:
        render_tree(src, project_dir, {"project_name": name})
        # Ensure conventional working directories exist.
        for sub in ("data", "logs", "skills"):
            (project_dir / sub).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        console.print(f"[red]Error:[/red] Failed to create project: {e}")
        raise typer.Exit(code=1) from None

    console.print(f"\n[green]Created[/green] {name} [dim](template: {template})[/dim]")
    console.print(f"  {project_dir}\n")
    console.print("[dim]Next steps:[/dim]")
    console.print(f"  cd {name}")
    extras = "".join(f"[{x}]" for x in spec.requires_extras)
    console.print(f'  pip install "neurocore-ai{extras}"')
    for skill in spec.suggested_skills:
        console.print(f"  pip install {skill}")
    console.print("  cp .env.example .env   # then add your keys")
    console.print("  neurocore run blueprints/*.flow.yaml")


# Make TEMPLATES importable for tests without circular import concerns.
__all__ = ["new_project", "TEMPLATES"]
