"""Integration test: neurocore init → validate → run end-to-end.

Tests the full init scaffold workflow: create a project, add a skill,
validate the blueprint, and run it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurocore.cli.app import app

runner = CliRunner()


class TestInitToRun:
    """End-to-end: init project, add skill, validate, run."""

    def test_init_creates_valid_project(self, tmp_path: Path):
        """neurocore init creates a project that can be validated."""
        # Step 1: Init
        result = runner.invoke(
            app, ["init", "my-agent", "--dir", str(tmp_path)]
        )
        assert result.exit_code == 0
        project_dir = tmp_path / "my-agent"
        assert (project_dir / "neurocore.yaml").exists()
        assert (project_dir / "blueprints" / "agent.flow.yaml").exists()

    def test_init_and_add_skill_then_validate(self, tmp_path: Path):
        """Init, write an echo skill, update the blueprint, validate."""
        # Init
        runner.invoke(app, ["init", "e2e-test", "--dir", str(tmp_path)])
        project = tmp_path / "e2e-test"

        # Add a skill
        (project / "skills" / "echo.py").write_text(
            "from flowengine import FlowContext\n"
            "from neurocore.skills.base import Skill, SkillMeta\n"
            "\n"
            "class EchoSkill(Skill):\n"
            "    skill_meta = SkillMeta(name='echo', version='0.1.0')\n"
            "    def process(self, context: FlowContext) -> FlowContext:\n"
            "        context.set('output', context.get('input', ''))\n"
            "        return context\n"
        )

        # Write a blueprint that references the skill
        bp = project / "blueprints" / "agent.flow.yaml"
        bp.write_text(
            "name: e2e-test-flow\n"
            "components:\n"
            "  - name: e1\n"
            "    type: echo\n"
            "flow:\n"
            "  type: sequential\n"
            "  steps:\n"
            "    - component: e1\n"
        )

        # Validate
        result = runner.invoke(
            app,
            ["validate", str(bp), "--project-root", str(project)],
        )
        assert result.exit_code == 0
        assert "Blueprint is valid" in result.output

    def test_init_add_skill_and_run(self, tmp_path: Path):
        """Full lifecycle: init → add skill → run blueprint."""
        runner.invoke(app, ["init", "e2e-run", "--dir", str(tmp_path)])
        project = tmp_path / "e2e-run"

        # Add echo skill
        (project / "skills" / "echo.py").write_text(
            "from flowengine import FlowContext\n"
            "from neurocore.skills.base import Skill, SkillMeta\n"
            "\n"
            "class EchoSkill(Skill):\n"
            "    skill_meta = SkillMeta(name='echo', version='0.1.0')\n"
            "    def process(self, context: FlowContext) -> FlowContext:\n"
            "        context.set('output', context.get('input', 'hello'))\n"
            "        return context\n"
        )

        bp = project / "blueprints" / "agent.flow.yaml"
        bp.write_text(
            "name: e2e-run\n"
            "components:\n"
            "  - name: echo\n"
            "    type: echo\n"
            "flow:\n"
            "  type: sequential\n"
            "  steps:\n"
            "    - component: echo\n"
        )

        # Run
        result = runner.invoke(
            app,
            [
                "run", str(bp),
                "--project-root", str(project),
                "--data", "input=world",
            ],
        )
        assert result.exit_code == 0
        assert "world" in result.output
