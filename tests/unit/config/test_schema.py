"""Tests for config/schema.py — Pydantic models, path resolution, skill config."""

from __future__ import annotations

from pathlib import Path

import pytest

from neurocore.config.schema import (
    LogFormat,
    LogLevel,
    LoggingConfig,
    NeuroCoreConfig,
    PathsConfig,
    ProjectConfig,
)


class TestProjectConfig:
    def test_defaults(self):
        cfg = ProjectConfig()
        assert cfg.name == "my-agent"
        assert cfg.version == "0.1.0"

    def test_custom_values(self):
        cfg = ProjectConfig(name="test-agent", version="1.2.3")
        assert cfg.name == "test-agent"
        assert cfg.version == "1.2.3"


class TestPathsConfig:
    def test_defaults(self):
        cfg = PathsConfig()
        assert cfg.skills == "skills"
        assert cfg.blueprints == "blueprints"
        assert cfg.data == "data"
        assert cfg.logs == "logs"

    def test_custom_paths(self):
        cfg = PathsConfig(skills="my-skills", data="/absolute/data")
        assert cfg.skills == "my-skills"
        assert cfg.data == "/absolute/data"


class TestLoggingConfig:
    def test_defaults(self):
        cfg = LoggingConfig()
        assert cfg.level == LogLevel.INFO
        assert cfg.format == LogFormat.CONSOLE
        assert cfg.file is None

    def test_custom_values(self):
        cfg = LoggingConfig(level="DEBUG", format="json", file="app.log")
        assert cfg.level == LogLevel.DEBUG
        assert cfg.format == LogFormat.JSON
        assert cfg.file == "app.log"

    def test_invalid_level_rejected(self):
        with pytest.raises(ValueError):
            LoggingConfig(level="INVALID")

    def test_invalid_format_rejected(self):
        with pytest.raises(ValueError):
            LoggingConfig(format="xml")


class TestNeuroCoreConfig:
    def test_all_defaults(self):
        cfg = NeuroCoreConfig()
        assert cfg.project.name == "my-agent"
        assert cfg.paths.skills == "skills"
        assert cfg.logging.level == LogLevel.INFO
        assert cfg.skills == {}

    def test_resolve_relative_path(self, tmp_path: Path):
        cfg = NeuroCoreConfig(project_root=tmp_path)
        resolved = cfg.resolve_path("skills")
        assert resolved == (tmp_path / "skills").resolve()
        assert resolved.is_absolute()

    def test_resolve_absolute_path(self, tmp_path: Path):
        abs_path = "/absolute/path/to/skills"
        cfg = NeuroCoreConfig(project_root=tmp_path)
        resolved = cfg.resolve_path(abs_path)
        assert resolved == Path(abs_path)

    def test_path_properties(self, tmp_path: Path):
        cfg = NeuroCoreConfig(project_root=tmp_path)
        assert cfg.skills_dir == (tmp_path / "skills").resolve()
        assert cfg.blueprints_dir == (tmp_path / "blueprints").resolve()
        assert cfg.data_dir == (tmp_path / "data").resolve()
        assert cfg.logs_dir == (tmp_path / "logs").resolve()

    def test_get_skill_config_present(self):
        cfg = NeuroCoreConfig(skills={"neuroweave": {"llm_provider": "anthropic"}})
        skill_cfg = cfg.get_skill_config("neuroweave")
        assert skill_cfg == {"llm_provider": "anthropic"}

    def test_get_skill_config_missing(self):
        cfg = NeuroCoreConfig()
        skill_cfg = cfg.get_skill_config("nonexistent")
        assert skill_cfg == {}

    def test_custom_paths_resolve(self, tmp_path: Path):
        cfg = NeuroCoreConfig(
            paths=PathsConfig(skills="custom-skills"),
            project_root=tmp_path,
        )
        assert cfg.skills_dir == (tmp_path / "custom-skills").resolve()
