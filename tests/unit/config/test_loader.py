"""Tests for config/loader.py — YAML loading, .env, env vars, path resolution."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from neurocore.config.loader import (
    _apply_env_overrides,
    _load_yaml,
    find_project_root,
    load_config,
)
from neurocore.config.schema import LogFormat, LogLevel
from neurocore.errors import ConfigError


class TestFindProjectRoot:
    def test_finds_root_in_current_dir(self, tmp_path: Path):
        (tmp_path / "neurocore.yaml").write_text("project:\n  name: test\n")
        root = find_project_root(tmp_path)
        assert root == tmp_path

    def test_finds_root_in_parent(self, tmp_path: Path):
        (tmp_path / "neurocore.yaml").write_text("project:\n  name: test\n")
        child = tmp_path / "subdir" / "deep"
        child.mkdir(parents=True)
        root = find_project_root(child)
        assert root == tmp_path

    def test_returns_none_when_not_found(self, tmp_path: Path):
        # tmp_path has no neurocore.yaml
        isolated = tmp_path / "isolated"
        isolated.mkdir()
        root = find_project_root(isolated)
        assert root is None


class TestLoadYaml:
    def test_loads_valid_yaml(self, tmp_path: Path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("project:\n  name: hello\n")
        data = _load_yaml(yaml_file)
        assert data == {"project": {"name": "hello"}}

    def test_empty_file_returns_empty_dict(self, tmp_path: Path):
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")
        data = _load_yaml(yaml_file)
        assert data == {}

    def test_missing_file_raises_config_error(self, tmp_path: Path):
        with pytest.raises(ConfigError, match="not found"):
            _load_yaml(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml_raises_config_error(self, tmp_path: Path):
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text("{{{{invalid yaml")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            _load_yaml(yaml_file)


class TestApplyEnvOverrides:
    def test_nested_env_var(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("NEUROCORE_LOGGING__LEVEL", "DEBUG")
        data: dict = {"logging": {"level": "INFO"}}
        _apply_env_overrides(data)
        assert data["logging"]["level"] == "DEBUG"

    def test_creates_intermediate_dicts(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("NEUROCORE_PROJECT__NAME", "env-agent")
        data: dict = {}
        _apply_env_overrides(data)
        assert data["project"]["name"] == "env-agent"

    def test_ignores_non_neurocore_vars(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OTHER_VAR", "value")
        data: dict = {}
        _apply_env_overrides(data)
        assert "other_var" not in data


class TestLoadConfig:
    def test_defaults_when_no_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Without a neurocore.yaml, should use built-in defaults."""
        monkeypatch.chdir(tmp_path)
        # Clear any NEUROCORE_ env vars
        for key in list(os.environ):
            if key.startswith("NEUROCORE_"):
                monkeypatch.delenv(key)
        cfg = load_config(project_root=tmp_path)
        assert cfg.project.name == "my-agent"
        assert cfg.logging.level == LogLevel.INFO
        assert cfg.project_root == tmp_path.resolve()

    def test_loads_yaml_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # Clear any NEUROCORE_ env vars
        for key in list(os.environ):
            if key.startswith("NEUROCORE_"):
                monkeypatch.delenv(key)
        yaml_content = """\
project:
  name: "yaml-agent"
  version: "2.0.0"
paths:
  skills: "my-skills"
logging:
  level: "DEBUG"
  format: "json"
skills:
  neuroweave:
    llm_provider: "anthropic"
"""
        (tmp_path / "neurocore.yaml").write_text(yaml_content)
        cfg = load_config(project_root=tmp_path)
        assert cfg.project.name == "yaml-agent"
        assert cfg.project.version == "2.0.0"
        assert cfg.paths.skills == "my-skills"
        assert cfg.logging.level == LogLevel.DEBUG
        assert cfg.logging.format == LogFormat.JSON
        assert cfg.skills["neuroweave"]["llm_provider"] == "anthropic"

    def test_env_vars_override_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        yaml_content = """\
project:
  name: "yaml-agent"
logging:
  level: "INFO"
"""
        (tmp_path / "neurocore.yaml").write_text(yaml_content)
        monkeypatch.setenv("NEUROCORE_LOGGING__LEVEL", "ERROR")
        cfg = load_config(project_root=tmp_path)
        # Env var wins over YAML
        assert cfg.logging.level == LogLevel.ERROR
        # YAML value preserved where no env override
        assert cfg.project.name == "yaml-agent"

    def test_dotenv_loaded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # Clear any NEUROCORE_ env vars
        for key in list(os.environ):
            if key.startswith("NEUROCORE_"):
                monkeypatch.delenv(key)
        (tmp_path / "neurocore.yaml").write_text("project:\n  name: yaml-name\n")
        (tmp_path / ".env").write_text("NEUROCORE_PROJECT__NAME=dotenv-name\n")
        cfg = load_config(project_root=tmp_path)
        assert cfg.project.name == "dotenv-name"

    def test_explicit_config_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # Clear any NEUROCORE_ env vars
        for key in list(os.environ):
            if key.startswith("NEUROCORE_"):
                monkeypatch.delenv(key)
        custom = tmp_path / "custom" / "my-config.yaml"
        custom.parent.mkdir(parents=True)
        custom.write_text("project:\n  name: custom-agent\n")
        cfg = load_config(config_path=custom)
        assert cfg.project.name == "custom-agent"
        # project_root defaults to config file's parent
        assert cfg.project_root == custom.parent

    def test_path_resolution(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # Clear any NEUROCORE_ env vars
        for key in list(os.environ):
            if key.startswith("NEUROCORE_"):
                monkeypatch.delenv(key)
        (tmp_path / "neurocore.yaml").write_text("paths:\n  skills: custom-skills\n")
        cfg = load_config(project_root=tmp_path)
        assert cfg.skills_dir == (tmp_path / "custom-skills").resolve()

    def test_invalid_yaml_raises(self, tmp_path: Path):
        bad = tmp_path / "neurocore.yaml"
        bad.write_text("{{{{not valid yaml")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_config(project_root=tmp_path)

    def test_skills_config_passthrough(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # Clear any NEUROCORE_ env vars
        for key in list(os.environ):
            if key.startswith("NEUROCORE_"):
                monkeypatch.delenv(key)
        yaml_content = """\
skills:
  web_search:
    provider: "tavily"
    max_results: 5
"""
        (tmp_path / "neurocore.yaml").write_text(yaml_content)
        cfg = load_config(project_root=tmp_path)
        assert cfg.get_skill_config("web_search") == {"provider": "tavily", "max_results": 5}
        assert cfg.get_skill_config("unknown") == {}
