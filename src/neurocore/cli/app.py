"""NeuroCore CLI application.

Top-level Typer app that registers all sub-commands.

Commands:
    neurocore init <name>           — scaffold a blank project
    neurocore new <template> <name> — scaffold from a template
    neurocore run <blueprint>       — execute a blueprint
    neurocore skill list            — list discovered skills
    neurocore skill info <name>     — show skill details
    neurocore validate <blueprint>  — validate without executing
    neurocore runs list             — list recorded runs
    neurocore runs inspect <id>     — show a run's history
    neurocore runs replay <id>      — re-execute a stored run
    neurocore runs resume <id>      — resume a suspended/failed run
    neurocore runs approve <id>     — approve a suspended approval gate
    neurocore --version             — show version
"""

from __future__ import annotations

import typer

from neurocore import __version__
from neurocore.cli.init_cmd import init_project
from neurocore.cli.mcp_cmd import mcp_app
from neurocore.cli.new_cmd import new_project
from neurocore.cli.run_cmd import run_blueprint
from neurocore.cli.runs_cmd import runs_app
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
app.command("new")(new_project)
app.command("run")(run_blueprint)
app.command("validate")(validate_blueprint_cmd)
app.add_typer(skill_app, name="skill")
app.add_typer(runs_app, name="runs")
app.add_typer(mcp_app, name="mcp")


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
