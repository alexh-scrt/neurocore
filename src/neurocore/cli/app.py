"""NeuroCore CLI application.

Top-level Typer app that registers all sub-commands.
"""

from __future__ import annotations

import typer

from neurocore import __version__

app = typer.Typer(
    name="neurocore",
    help="NeuroCore — pluggable, YAML-driven framework for agentic AI applications.",
    no_args_is_help=True,
    add_completion=False,
)


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
