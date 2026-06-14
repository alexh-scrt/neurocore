"""Tests for A5 — the `neurocore runs` CLI sub-app."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurocore.cli.app import app

runner = CliRunner()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal project with a sequential blueprint and a local skill."""
    (tmp_path / "neurocore.yaml").write_text(textwrap.dedent("""
        project:
          name: test
        persistence:
          backend: sqlite
    """))
    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "hello.py").write_text(textwrap.dedent('''
        from flowengine import FlowContext
        from neurocore.skills.base import Skill, SkillMeta

        class HelloSkill(Skill):
            skill_meta = SkillMeta(name="hello", version="0.1.0", provides=["msg"])
            def process(self, context):
                context.set("msg", "hi")
                return context
    '''))
    bp = tmp_path / "blueprints"
    bp.mkdir()
    (bp / "flow.yaml").write_text(textwrap.dedent("""
        name: hello-flow
        components:
          - name: hello
            type: hello
        flow:
          type: sequential
          steps:
            - component: hello
    """))
    return tmp_path


def _seed_run(project: Path) -> str:
    """Run the blueprint once and return the resulting run id."""
    result = runner.invoke(
        app, ["run", str(project / "blueprints" / "flow.yaml"),
              "--project-root", str(project)],
    )
    assert result.exit_code == 0, result.output
    # Fetch the run id from the store.
    from neurocore.config.loader import load_config
    from neurocore.persistence import build_run_store

    store = build_run_store(load_config(project_root=project))
    runs = store.list_runs()
    assert runs
    return runs[0].run_id


def test_runs_list_empty(project: Path):
    result = runner.invoke(app, ["runs", "list", "--project-root", str(project)])
    assert result.exit_code == 0
    assert "No runs recorded" in result.output


def test_runs_list_shows_run(project: Path):
    _seed_run(project)
    result = runner.invoke(app, ["runs", "list", "--project-root", str(project)])
    assert result.exit_code == 0
    assert "hello-flow" in result.output
    assert "completed" in result.output


def test_runs_inspect(project: Path):
    rid = _seed_run(project)
    result = runner.invoke(
        app, ["runs", "inspect", rid[:8], "--project-root", str(project)]
    )
    assert result.exit_code == 0
    assert "hello-flow" in result.output
    assert "hello" in result.output  # step component


def test_runs_inspect_json(project: Path):
    rid = _seed_run(project)
    result = runner.invoke(
        app, ["runs", "inspect", rid, "--json", "--project-root", str(project)]
    )
    assert result.exit_code == 0
    import json
    payload = json.loads(result.output)
    assert payload["run"]["blueprint_name"] == "hello-flow"
    assert payload["steps"][0]["component"] == "hello"


def test_runs_inspect_unknown_id(project: Path):
    result = runner.invoke(
        app, ["runs", "inspect", "deadbeef", "--project-root", str(project)]
    )
    assert result.exit_code != 0


def test_runs_replay_creates_new_run(project: Path):
    rid = _seed_run(project)
    result = runner.invoke(
        app, ["runs", "replay", rid, "--project-root", str(project)]
    )
    assert result.exit_code == 0
    from neurocore.config.loader import load_config
    from neurocore.persistence import build_run_store

    store = build_run_store(load_config(project_root=project))
    assert len(store.list_runs()) == 2  # original + replay


def test_runs_approve_resumes_suspended(project: Path):
    # Add an approval gate to the blueprint.
    (project / "blueprints" / "approve.yaml").write_text(textwrap.dedent("""
        name: approve-flow
        components:
          - name: hello
            type: hello
        flow:
          type: sequential
          steps:
            - component: hello
            - approval: {name: gate}
    """))
    run_res = runner.invoke(
        app, ["run", str(project / "blueprints" / "approve.yaml"),
              "--project-root", str(project)],
    )
    assert run_res.exit_code == 0

    from neurocore.config.loader import load_config
    from neurocore.persistence import RunStatus, build_run_store

    store = build_run_store(load_config(project_root=project))
    suspended = store.list_runs(status=RunStatus.SUSPENDED)
    assert suspended, "expected a suspended run"
    rid = suspended[0].run_id

    approve = runner.invoke(
        app, ["runs", "approve", rid, "--by", "alexh@scrtlabs.com",
              "--project-root", str(project)],
    )
    assert approve.exit_code == 0, approve.output
    assert "approved" in approve.output.lower()

    store2 = build_run_store(load_config(project_root=project))
    assert store2.load_run(rid).status == RunStatus.COMPLETED
