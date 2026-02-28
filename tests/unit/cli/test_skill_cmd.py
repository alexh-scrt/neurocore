"""T13: Tests for `neurocore skill list/info` commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurocore.cli.app import app

runner = CliRunner()


def _create_project_with_skills(tmp_path: Path) -> Path:
    """Create a project with two skills."""
    (tmp_path / "neurocore.yaml").write_text(
        "project:\n  name: test\n"
        "skills:\n"
        "  echo:\n"
        "    message: hello\n"
    )

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "echo_skill.py").write_text(
        "from flowengine import FlowContext\n"
        "from neurocore.skills.base import Skill, SkillMeta\n"
        "\n"
        "class EchoSkill(Skill):\n"
        "    skill_meta = SkillMeta(\n"
        "        name='echo',\n"
        "        version='1.0.0',\n"
        "        description='Echoes input',\n"
        "        tags=['utility', 'test'],\n"
        "        provides=['echo_output'],\n"
        "        consumes=['input'],\n"
        "    )\n"
        "    def process(self, context: FlowContext) -> FlowContext:\n"
        "        return context\n"
    )
    (skills_dir / "upper_skill.py").write_text(
        "from flowengine import FlowContext\n"
        "from neurocore.skills.base import Skill, SkillMeta\n"
        "\n"
        "class UpperSkill(Skill):\n"
        "    skill_meta = SkillMeta(\n"
        "        name='upper',\n"
        "        version='0.2.0',\n"
        "        description='Uppercases text',\n"
        "    )\n"
        "    def process(self, context: FlowContext) -> FlowContext:\n"
        "        return context\n"
    )
    return tmp_path


class TestSkillList:
    def test_lists_discovered_skills(self, tmp_path: Path):
        _create_project_with_skills(tmp_path)
        result = runner.invoke(
            app, ["skill", "list", "--project-root", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "echo" in result.output
        assert "upper" in result.output

    def test_shows_version(self, tmp_path: Path):
        _create_project_with_skills(tmp_path)
        result = runner.invoke(
            app, ["skill", "list", "--project-root", str(tmp_path)]
        )
        assert "1.0.0" in result.output
        assert "0.2.0" in result.output

    def test_shows_description(self, tmp_path: Path):
        _create_project_with_skills(tmp_path)
        result = runner.invoke(
            app, ["skill", "list", "--project-root", str(tmp_path)]
        )
        assert "Echoes input" in result.output

    def test_shows_count(self, tmp_path: Path):
        _create_project_with_skills(tmp_path)
        result = runner.invoke(
            app, ["skill", "list", "--project-root", str(tmp_path)]
        )
        # At least 2 directory skills + any entry point skills
        assert "skill(s) found" in result.output

    def test_empty_skills_directory_still_shows_entry_points(self, tmp_path: Path):
        (tmp_path / "neurocore.yaml").write_text("project:\n  name: test\n")
        (tmp_path / "skills").mkdir()
        result = runner.invoke(
            app, ["skill", "list", "--project-root", str(tmp_path)]
        )
        assert result.exit_code == 0
        # Entry point skills (neuroweave) are still discovered
        assert "skill(s) found" in result.output


class TestSkillInfo:
    def test_shows_skill_details(self, tmp_path: Path):
        _create_project_with_skills(tmp_path)
        result = runner.invoke(
            app, ["skill", "info", "echo", "--project-root", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "echo" in result.output
        assert "1.0.0" in result.output

    def test_shows_provides_and_consumes(self, tmp_path: Path):
        _create_project_with_skills(tmp_path)
        result = runner.invoke(
            app, ["skill", "info", "echo", "--project-root", str(tmp_path)]
        )
        assert "echo_output" in result.output
        assert "input" in result.output

    def test_shows_tags(self, tmp_path: Path):
        _create_project_with_skills(tmp_path)
        result = runner.invoke(
            app, ["skill", "info", "echo", "--project-root", str(tmp_path)]
        )
        assert "utility" in result.output
        assert "test" in result.output

    def test_shows_health_status(self, tmp_path: Path):
        _create_project_with_skills(tmp_path)
        result = runner.invoke(
            app, ["skill", "info", "echo", "--project-root", str(tmp_path)]
        )
        assert "healthy" in result.output

    def test_unknown_skill_fails(self, tmp_path: Path):
        _create_project_with_skills(tmp_path)
        result = runner.invoke(
            app, ["skill", "info", "nonexistent", "--project-root", str(tmp_path)]
        )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_unknown_skill_shows_available(self, tmp_path: Path):
        _create_project_with_skills(tmp_path)
        result = runner.invoke(
            app, ["skill", "info", "nonexistent", "--project-root", str(tmp_path)]
        )
        assert "echo" in result.output
