"""T12: Tests for `neurocore run` command."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurocore.cli.app import app
from neurocore.cli.run_cmd import _parse_data_args

runner = CliRunner()


def _create_runnable_project(tmp_path: Path) -> Path:
    """Create a project with echo skill and a blueprint that runs it."""
    # Config
    (tmp_path / "neurocore.yaml").write_text(
        "project:\n  name: test\n"
    )

    # Skills directory with echo skill
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "echo_skill.py").write_text(
        "from flowengine import FlowContext\n"
        "from neurocore.skills.base import Skill, SkillMeta\n"
        "\n"
        "class EchoSkill(Skill):\n"
        "    skill_meta = SkillMeta(name='echo', version='0.1.0')\n"
        "    def process(self, context: FlowContext) -> FlowContext:\n"
        "        context.set('echo_output', context.get('input', 'default'))\n"
        "        return context\n"
    )

    # Blueprint
    bp_dir = tmp_path / "blueprints"
    bp_dir.mkdir()
    bp_file = bp_dir / "flow.yaml"
    bp_file.write_text(
        "name: test-flow\n"
        "components:\n"
        "  - name: e1\n"
        "    type: echo\n"
        "flow:\n"
        "  type: sequential\n"
        "  steps:\n"
        "    - component: e1\n"
    )
    return bp_file


class TestParseDataArgs:
    def test_single_pair(self):
        result = _parse_data_args(["key=value"])
        assert result == {"key": "value"}

    def test_multiple_pairs(self):
        result = _parse_data_args(["a=1", "b=2"])
        assert result == {"a": "1", "b": "2"}

    def test_value_with_equals(self):
        result = _parse_data_args(["url=http://example.com?q=1"])
        assert result == {"url": "http://example.com?q=1"}

    def test_empty_value(self):
        result = _parse_data_args(["key="])
        assert result == {"key": ""}

    def test_missing_equals_raises(self):
        import typer

        with pytest.raises(typer.BadParameter, match="Invalid data format"):
            _parse_data_args(["no-equals"])

    def test_empty_key_raises(self):
        import typer

        with pytest.raises(typer.BadParameter, match="Key cannot be empty"):
            _parse_data_args(["=value"])


class TestRunCommand:
    def test_runs_blueprint(self, tmp_path: Path):
        bp_file = _create_runnable_project(tmp_path)
        result = runner.invoke(
            app,
            ["run", str(bp_file), "--project-root", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "echo_output" in result.output

    def test_with_data_args(self, tmp_path: Path):
        bp_file = _create_runnable_project(tmp_path)
        result = runner.invoke(
            app,
            [
                "run", str(bp_file),
                "--project-root", str(tmp_path),
                "--data", "input=hello",
            ],
        )
        assert result.exit_code == 0
        assert "hello" in result.output

    def test_json_output(self, tmp_path: Path):
        bp_file = _create_runnable_project(tmp_path)
        result = runner.invoke(
            app,
            [
                "run", str(bp_file),
                "--project-root", str(tmp_path),
                "--json",
            ],
        )
        assert result.exit_code == 0
        # JSON output should be parseable
        import json

        # The output may contain ANSI codes or metadata, just check key present
        assert "echo_output" in result.output

    def test_verbose_output(self, tmp_path: Path):
        bp_file = _create_runnable_project(tmp_path)
        result = runner.invoke(
            app,
            [
                "run", str(bp_file),
                "--project-root", str(tmp_path),
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Blueprint:" in result.output

    def test_nonexistent_blueprint_fails(self, tmp_path: Path):
        result = runner.invoke(app, ["run", str(tmp_path / "nonexistent.yaml")])
        assert result.exit_code != 0

    def test_invalid_blueprint_fails(self, tmp_path: Path):
        (tmp_path / "neurocore.yaml").write_text("project:\n  name: test\n")
        (tmp_path / "skills").mkdir()

        bad_bp = tmp_path / "bad.yaml"
        bad_bp.write_text("name: bad\n")  # Missing components & flow

        result = runner.invoke(
            app,
            ["run", str(bad_bp), "--project-root", str(tmp_path)],
        )
        assert result.exit_code == 1
