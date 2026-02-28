"""T11: Tests for `neurocore init` command."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurocore.cli.app import app

runner = CliRunner()


class TestInitCommand:
    def test_creates_project_directory(self, tmp_path: Path):
        result = runner.invoke(app, ["init", "my-agent", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / "my-agent").is_dir()

    def test_creates_subdirectories(self, tmp_path: Path):
        runner.invoke(app, ["init", "my-agent", "--dir", str(tmp_path)])
        project = tmp_path / "my-agent"
        assert (project / "skills").is_dir()
        assert (project / "blueprints").is_dir()
        assert (project / "data").is_dir()
        assert (project / "logs").is_dir()

    def test_creates_config_file(self, tmp_path: Path):
        runner.invoke(app, ["init", "my-agent", "--dir", str(tmp_path)])
        config = tmp_path / "my-agent" / "neurocore.yaml"
        assert config.exists()
        content = config.read_text()
        assert "my-agent" in content
        assert "project:" in content

    def test_creates_env_example(self, tmp_path: Path):
        runner.invoke(app, ["init", "my-agent", "--dir", str(tmp_path)])
        env = tmp_path / "my-agent" / ".env.example"
        assert env.exists()
        content = env.read_text()
        assert "NEUROCORE" in content

    def test_creates_example_blueprint(self, tmp_path: Path):
        runner.invoke(app, ["init", "my-agent", "--dir", str(tmp_path)])
        bp = tmp_path / "my-agent" / "blueprints" / "agent.flow.yaml"
        assert bp.exists()
        content = bp.read_text()
        assert "my-agent" in content

    def test_project_name_in_templates(self, tmp_path: Path):
        runner.invoke(app, ["init", "cool-project", "--dir", str(tmp_path)])
        config = tmp_path / "cool-project" / "neurocore.yaml"
        content = config.read_text()
        assert "cool-project" in content

    def test_existing_directory_fails(self, tmp_path: Path):
        (tmp_path / "existing").mkdir()
        result = runner.invoke(app, ["init", "existing", "--dir", str(tmp_path)])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_success_message(self, tmp_path: Path):
        result = runner.invoke(app, ["init", "my-agent", "--dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "Created NeuroCore project" in result.output
        assert "my-agent" in result.output

    def test_shows_next_steps(self, tmp_path: Path):
        result = runner.invoke(app, ["init", "my-agent", "--dir", str(tmp_path)])
        assert "Next steps" in result.output
        assert "cd my-agent" in result.output

    def test_shows_tree_structure(self, tmp_path: Path):
        result = runner.invoke(app, ["init", "my-agent", "--dir", str(tmp_path)])
        assert "neurocore.yaml" in result.output
        assert "skills/" in result.output
        assert "blueprints/" in result.output

    def test_name_required(self):
        result = runner.invoke(app, ["init"])
        assert result.exit_code != 0
