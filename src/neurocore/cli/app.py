"""NeuroCore CLI application.

Top-level Typer app that registers all sub-commands.

Commands:
    neurocore init <name>           — scaffold a new project
    neurocore run <blueprint>       — execute a blueprint
    neurocore skill list            — list discovered skills
    neurocore skill info <name>     — show skill details
    neurocore validate <blueprint>  — validate without executing
    neurocore --version             — show version
"""

from __future__ import annotations

import typer

from neurocore import __version__
from neurocore.cli.init_cmd import init_project
from neurocore.cli.run_cmd import run_blueprint
from neurocore.cli.skill_cmd import skill_app
from neurocore.cli.validate_cmd import validate_blueprint_cmd

app = typer.Typer(
    name="neurocore",
    help="NeuroCore — pluggable, YAML-driven framework for agentic AI applications.",
    no_args_is_help=True,
    add_completion=False,
)

# Register commands
app.command("init")(init_project)
app.command("run")(run_blueprint)
app.command("validate")(validate_blueprint_cmd)
app.add_typer(skill_app, name="skill")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"neurocore {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """NeuroCore CLI."""
