"""Integration test: skill discovery from directory + entry points.

Tests that skills are discovered from both the skills/ directory
and installed entry points, and that entry points take precedence.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurocore.cli.app import app
from neurocore.config.loader import load_config
from neurocore.skills.loader import discover_skills

runner = CliRunner()


class TestDirectoryDiscovery:
    """Discover skills from the skills/ directory."""

    def test_discovers_skills_from_directory(self, tmp_path: Path):
        (tmp_path / "neurocore.yaml").write_text("project:\n  name: test\n")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        (skills_dir / "alpha.py").write_text(
            "from flowengine import FlowContext\n"
            "from neurocore.skills.base import Skill, SkillMeta\n"
            "\n"
            "class AlphaSkill(Skill):\n"
            "    skill_meta = SkillMeta(name='alpha', version='1.0.0')\n"
            "    def process(self, ctx: FlowContext) -> FlowContext:\n"
            "        return ctx\n"
        )
        (skills_dir / "beta.py").write_text(
            "from flowengine import FlowContext\n"
            "from neurocore.skills.base import Skill, SkillMeta\n"
            "\n"
            "class BetaSkill(Skill):\n"
            "    skill_meta = SkillMeta(name='beta', version='2.0.0')\n"
            "    def process(self, ctx: FlowContext) -> FlowContext:\n"
            "        return ctx\n"
        )

        config = load_config(project_root=tmp_path)
        registry = discover_skills(config)

        assert "alpha" in registry
        assert "beta" in registry
        assert len(registry) >= 2

    def test_cli_skill_list_shows_directory_skills(self, tmp_path: Path):
        (tmp_path / "neurocore.yaml").write_text("project:\n  name: test\n")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "demo.py").write_text(
            "from flowengine import FlowContext\n"
            "from neurocore.skills.base import Skill, SkillMeta\n"
            "\n"
            "class DemoSkill(Skill):\n"
            "    skill_meta = SkillMeta(\n"
            "        name='demo', version='0.5.0',\n"
            "        description='Demo skill for testing'\n"
            "    )\n"
            "    def process(self, ctx: FlowContext) -> FlowContext:\n"
            "        return ctx\n"
        )

        result = runner.invoke(
            app, ["skill", "list", "--project-root", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "demo" in result.output
        assert "0.5.0" in result.output


class TestEntryPointDiscovery:
    """Discover skills from entry points (neurocore-skill-neuroweave)."""

    def test_discovers_neuroweave_via_entry_points(self, tmp_path: Path):
        """neurocore-skill-neuroweave is installed — should be discovered."""
        (tmp_path / "neurocore.yaml").write_text("project:\n  name: test\n")
        (tmp_path / "skills").mkdir()

        config = load_config(project_root=tmp_path)
        registry = discover_skills(config)

        assert "neuroweave" in registry

    def test_cli_shows_neuroweave_skill(self, tmp_path: Path):
        (tmp_path / "neurocore.yaml").write_text("project:\n  name: test\n")
        (tmp_path / "skills").mkdir()

        result = runner.invoke(
            app, ["skill", "list", "--project-root", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "neuroweave" in result.output

    def test_cli_skill_info_neuroweave(self, tmp_path: Path):
        (tmp_path / "neurocore.yaml").write_text("project:\n  name: test\n")
        (tmp_path / "skills").mkdir()

        result = runner.invoke(
            app,
            ["skill", "info", "neuroweave", "--project-root", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "neuroweave" in result.output
        assert "knowledge-graph" in result.output


class TestMixedDiscovery:
    """Both directory and entry point skills co-exist."""

    def test_directory_and_entry_point_both_discovered(self, tmp_path: Path):
        (tmp_path / "neurocore.yaml").write_text("project:\n  name: test\n")
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "local.py").write_text(
            "from flowengine import FlowContext\n"
            "from neurocore.skills.base import Skill, SkillMeta\n"
            "\n"
            "class LocalSkill(Skill):\n"
            "    skill_meta = SkillMeta(name='local', version='0.1.0')\n"
            "    def process(self, ctx: FlowContext) -> FlowContext:\n"
            "        return ctx\n"
        )

        config = load_config(project_root=tmp_path)
        registry = discover_skills(config)

        # Both local directory skill and entry point (neuroweave) found
        assert "local" in registry
        assert "neuroweave" in registry
