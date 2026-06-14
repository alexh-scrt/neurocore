"""neurocore init — scaffold a new project.

Creates a new NeuroCore project with:
- neurocore.yaml (configuration)
- .env.example (environment template)
- blueprints/ directory with example blueprint
- skills/ directory
- data/ directory
- logs/ directory

Usage:
    neurocore init my-agent
    neurocore init my-agent --dir /path/to/projects
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from neurocore.scaffold.render import TEMPLATES_DIR as _TEMPLATES_DIR
from neurocore.scaffold.render import render_template as _render_template

console = Console()


def init_project(
    name: str = typer.Argument(
        help="Project name (used for directory and config).",
    ),
    directory: Path = typer.Option(
        Path("."),
        "--dir",
        "-d",
        help="Parent directory to create the project in.",
    ),
) -> None:
    """Scaffold a new NeuroCore project."""
    project_dir = directory.resolve() / name

    # Check if directory already exists
    if project_dir.exists():
        console.print(
            f"[red]Error:[/red] Directory '{project_dir}' already exists."
        )
        raise typer.Exit(code=1)

    context = {"project_name": name}

    try:
        # Create directory structure
        project_dir.mkdir(parents=True)
        (project_dir / "skills").mkdir()
        (project_dir / "blueprints").mkdir()
        (project_dir / "data").mkdir()
        (project_dir / "logs").mkdir()

        # Render and write config file
        config_content = _render_template(
            _TEMPLATES_DIR / "neurocore.yaml", context
        )
        (project_dir / "neurocore.yaml").write_text(config_content)

        # Render and write .env.example
        env_content = _render_template(
            _TEMPLATES_DIR / ".env.example", context
        )
        (project_dir / ".env.example").write_text(env_content)

        # Render and write example blueprint
        blueprint_content = _render_template(
            _TEMPLATES_DIR / "agent.flow.yaml", context
        )
        (project_dir / "blueprints" / "agent.flow.yaml").write_text(
            blueprint_content
        )

    except OSError as e:
        console.print(f"[red]Error:[/red] Failed to create project: {e}")
        raise typer.Exit(code=1) from None

    # Success output
    console.print()
    console.print(f"[green]Created NeuroCore project:[/green] {name}")
    console.print()
    console.print(f"  [dim]{project_dir}/[/dim]")
    console.print(f"  ├── neurocore.yaml")
    console.print(f"  ├── .env.example")
    console.print(f"  ├── blueprints/")
    console.print(f"  │   └── agent.flow.yaml")
    console.print(f"  ├── skills/")
    console.print(f"  ├── data/")
    console.print(f"  └── logs/")
    console.print()
    console.print("[dim]Next steps:[/dim]")
    console.print(f"  cd {name}")
    console.print(f"  cp .env.example .env")
    console.print(f"  neurocore run blueprints/agent.flow.yaml")
