"""neurocore runs — inspect, replay, resume, and approve execution history.

Usage:
    neurocore runs list [--status suspended] [--blueprint research] [--limit 20]
    neurocore runs inspect <run_id> [--full] [--json]
    neurocore runs replay <run_id>
    neurocore runs resume <run_id> [--data key=value ...]
    neurocore runs approve <run_id> [--reject] [--note "..."] [--by you@example.com]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from neurocore.errors import NeuroCoreError

if TYPE_CHECKING:
    from neurocore.config.schema import NeuroCoreConfig
    from neurocore.persistence import RunRecord, RunStore

console = Console(stderr=True)
output_console = Console()

runs_app = typer.Typer(
    name="runs",
    help="Inspect, replay, resume, and approve blueprint runs.",
    no_args_is_help=True,
)

_STATUS_COLORS = {
    "completed": "green",
    "failed": "red",
    "suspended": "yellow",
    "running": "cyan",
    "cancelled": "dim",
}


def _load_store(
    project_root: Optional[Path],
) -> tuple[NeuroCoreConfig, RunStore]:
    from neurocore.config.loader import load_config
    from neurocore.persistence import build_run_store

    config = load_config(project_root=project_root)
    store = build_run_store(config)
    if store is None:
        console.print(
            "[red]Persistence is disabled.[/red] Enable it in neurocore.yaml "
            "(persistence.enabled: true) to use run history."
        )
        raise typer.Exit(code=1)
    return config, store


def _resolve_run(store: RunStore, partial: str) -> RunRecord:
    """Resolve a full or prefix run id to a single RunRecord."""
    run = store.load_run(partial)
    if run is not None:
        return run
    matches = [r for r in store.list_runs(limit=1000) if r.run_id.startswith(partial)]
    if not matches:
        raise typer.BadParameter(f"No run found matching '{partial}'.")
    if len(matches) > 1:
        ids = ", ".join(r.run_id[:12] for r in matches[:5])
        raise typer.BadParameter(f"Ambiguous run id '{partial}'. Matches: {ids} …")
    return matches[0]


def _status_text(status: str) -> str:
    color = _STATUS_COLORS.get(status, "white")
    return f"[{color}]{status}[/{color}]"


@runs_app.command("list")
def runs_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status."),
    blueprint: Optional[str] = typer.Option(None, "--blueprint", "-b",
                                             help="Filter by blueprint name."),
    limit: int = typer.Option(50, "--limit", "-n", help="Max rows."),
    project_root: Optional[Path] = typer.Option(None, "--project-root", "-p"),
) -> None:
    """List recorded runs (newest first)."""
    from neurocore.persistence import RunStatus

    _, store = _load_store(project_root)
    status_filter = RunStatus(status) if status else None
    runs = store.list_runs(status=status_filter, blueprint=blueprint, limit=limit)
    if not runs:
        console.print("[dim]No runs recorded.[/dim]")
        return

    table = Table(title="Runs")
    table.add_column("Run ID", style="cyan", no_wrap=True)
    table.add_column("Blueprint")
    table.add_column("Status")
    table.add_column("Steps", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Started", style="dim")
    for run in runs:
        n_steps = len(store.load_steps(run.run_id))
        dur = f"{run.duration_ms / 1000:.2f}s" if run.duration_ms else "—"
        table.add_row(
            run.run_id[:12], run.blueprint_name, _status_text(run.status),
            str(n_steps), dur, run.created_at[:19],
        )
    output_console.print(table)


@runs_app.command("inspect")
def runs_inspect(
    run_id: str = typer.Argument(help="Run id (full or unique prefix)."),
    full: bool = typer.Option(False, "--full", help="Show the final context data."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Emit JSON."),
    project_root: Optional[Path] = typer.Option(None, "--project-root", "-p"),
) -> None:
    """Show a run's details and step history."""
    _, store = _load_store(project_root)
    run = _resolve_run(store, run_id)
    steps = store.load_steps(run.run_id)

    if output_json:
        payload = {"run": run.model_dump(), "steps": [s.model_dump() for s in steps]}
        # Emit raw (not via rich) so the JSON is not soft-wrapped/mangled.
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    lines = [
        f"[bold]{run.blueprint_name}[/bold] v{run.blueprint_version}",
        f"Run ID: {run.run_id}",
        f"Status: {_status_text(run.status)}",
        f"Flow: {run.flow_type}",
    ]
    if run.duration_ms:
        lines.append(f"Duration: {run.duration_ms / 1000:.2f}s")
    if run.error:
        lines.append(f"[red]Error:[/red] {run.error}")
    if run.suspended_at_node:
        lines.append(f"[yellow]Suspended at:[/yellow] {run.suspended_at_node} "
                     f"({run.suspension_reason or ''})")
    output_console.print(Panel("\n".join(lines), title="Run", border_style="cyan"))

    if steps:
        table = Table(title="Steps")
        table.add_column("#", justify="right")
        table.add_column("Component")
        table.add_column("Status")
        table.add_column("Duration", justify="right")
        table.add_column("Outputs", style="dim")
        table.add_column("Error", style="red")
        for s in steps:
            dur = f"{s.duration_ms:.0f}ms" if s.duration_ms else "—"
            table.add_row(
                str(s.step_index), s.component, _status_text(s.status), dur,
                ", ".join(s.output_keys), s.error or "",
            )
        output_console.print(table)

    if full and run.final_context:
        data = run.final_context.get("data", {})
        syntax = Syntax(json.dumps(data, indent=2, default=str), "json", theme="monokai")
        output_console.print(Panel(syntax, title="Final context", border_style="green"))


@runs_app.command("replay")
def runs_replay(
    run_id: str = typer.Argument(help="Run id (full or unique prefix)."),
    project_root: Optional[Path] = typer.Option(None, "--project-root", "-p"),
) -> None:
    """Re-execute a stored run from its original inputs (creates a new run)."""
    from neurocore.runtime.blueprint import Blueprint
    from neurocore.runtime.executor import execute_blueprint_tracked
    from neurocore.skills.loader import discover_skills

    config, store = _load_store(project_root)
    run = _resolve_run(store, run_id)
    try:
        blueprint = Blueprint(**run.blueprint_snapshot)
        registry = discover_skills(config)
        result = execute_blueprint_tracked(
            blueprint, registry, config,
            initial_data=run.initial_data, run_store=store,
        )
    except NeuroCoreError as e:
        console.print(f"[red]Replay failed:[/red] {e}")
        raise typer.Exit(code=1) from None
    _print_result(result)


@runs_app.command("resume")
def runs_resume(
    run_id: str = typer.Argument(help="Run id (full or unique prefix)."),
    data: list[str] = typer.Option([], "--data", "-d",
                                   help="resume_data as KEY=VALUE pairs."),
    project_root: Optional[Path] = typer.Option(None, "--project-root", "-p"),
) -> None:
    """Resume a suspended or failed run."""
    from neurocore.cli.run_cmd import _parse_data_args
    from neurocore.runtime.executor import resume_blueprint
    from neurocore.skills.loader import discover_skills

    config, store = _load_store(project_root)
    run = _resolve_run(store, run_id)
    resume_data = _parse_data_args(data) if data else None
    try:
        registry = discover_skills(config)
        result = resume_blueprint(
            run.run_id, registry, config,
            resume_data=resume_data, run_store=store,
        )
    except NeuroCoreError as e:
        console.print(f"[red]Resume failed:[/red] {e}")
        raise typer.Exit(code=1) from None
    _print_result(result)


@runs_app.command("approve")
def runs_approve(
    run_id: str = typer.Argument(help="Run id (full or unique prefix)."),
    reject: bool = typer.Option(False, "--reject", help="Reject instead of approve."),
    note: str = typer.Option("", "--note", help="Optional decision note."),
    by: str = typer.Option("", "--by", help="Who made the decision."),
    project_root: Optional[Path] = typer.Option(None, "--project-root", "-p"),
) -> None:
    """Approve (or --reject) a suspended approval gate and resume the run."""
    from neurocore.runtime.executor import resume_blueprint
    from neurocore.skills.loader import discover_skills

    config, store = _load_store(project_root)
    run = _resolve_run(store, run_id)
    decision = {"approved": not reject, "note": note, "by": by}
    try:
        registry = discover_skills(config)
        result = resume_blueprint(
            run.run_id, registry, config,
            resume_data=decision, run_store=store,
        )
    except NeuroCoreError as e:
        verb = "Rejection" if reject else "Approval"
        console.print(f"[red]{verb} failed:[/red] {e}")
        raise typer.Exit(code=1) from None
    action = "rejected" if reject else "approved"
    console.print(f"[green]Run {action}.[/green]")
    _print_result(result)


def _print_result(result: object) -> None:
    """Render a final FlowContext as a result panel (matches `neurocore run`)."""
    data = result.data.to_dict() if hasattr(result.data, "to_dict") else dict(result.data)  # type: ignore[attr-defined]
    syntax = Syntax(json.dumps(data, indent=2, default=str), "json", theme="monokai")
    output_console.print(Panel(syntax, title="[green]Result[/green]", border_style="green"))
