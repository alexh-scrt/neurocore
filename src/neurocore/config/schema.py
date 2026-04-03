"""Pydantic models for neurocore.yaml configuration.

The config hierarchy mirrors the YAML structure:

    project:
      name: "my-agent"
      version: "0.1.0"
    paths:
      skills: "skills"
      blueprints: "blueprints"
      data: "data"
      logs: "logs"
    logging:
      level: "INFO"
      format: "console"
      file: null
    skills:
      neuroweave:
        llm_provider: "anthropic"
        ...

Environment variable override uses ``NEUROCORE_`` prefix with double
underscore for nesting: ``NEUROCORE_LOGGING__LEVEL=DEBUG``
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from neurocore.config.defaults import (
    DEFAULT_BLUEPRINTS_DIR,
    DEFAULT_DATA_DIR,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOGS_DIR,
    DEFAULT_PROJECT_NAME,
    DEFAULT_PROJECT_VERSION,
    DEFAULT_SKILLS_DIR,
)


class LogLevel(str, Enum):
    """Supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogFormat(str, Enum):
    """Supported log output formats."""

    CONSOLE = "console"
    JSON = "json"


class ProjectConfig(BaseModel):
    """Project metadata."""

    name: str = DEFAULT_PROJECT_NAME
    version: str = DEFAULT_PROJECT_VERSION


class PathsConfig(BaseModel):
    """Directory paths (relative to project root or absolute).

    Relative paths are resolved against `project_root` at load time
    by the ConfigLoader.
    """

    skills: str = DEFAULT_SKILLS_DIR
    blueprints: str = DEFAULT_BLUEPRINTS_DIR
    data: str = DEFAULT_DATA_DIR
    logs: str = DEFAULT_LOGS_DIR


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: LogLevel = LogLevel(DEFAULT_LOG_LEVEL)
    format: LogFormat = LogFormat(DEFAULT_LOG_FORMAT)
    file: str | None = None


class LLMConfig(BaseModel):
    """Project-level LLM configuration shared across all skills that set requires_llm=True."""

    provider: str = ""  # "anthropic" | "openai" | "mock" | ""
    model: str = ""  # provider-specific model identifier
    api_key: str = ""  # read from env: NEUROCORE_LLM__API_KEY
    max_tokens: int = 8192
    temperature: float = 1.0


class NeuroCoreConfig(BaseModel):
    """Top-level NeuroCore configuration model.

    Represents the full contents of neurocore.yaml plus any
    overrides from .env and environment variables.

    Attributes:
        project: Project metadata (name, version).
        paths: Directory paths for skills, blueprints, data, logs.
        logging: Logging level, format, optional file output.
        llm: Project-level LLM configuration.
        skills: Per-skill configuration dicts, keyed by skill name.
        project_root: Resolved absolute path to the project root
                      (the directory containing neurocore.yaml).
                      Set by the ConfigLoader, not from YAML.
    """

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    skills: dict[str, dict[str, Any]] = Field(default_factory=dict)
    project_root: Path = Field(default_factory=lambda: Path.cwd())

    def resolve_path(self, relative_path: str) -> Path:
        """Resolve a path relative to project_root.

        Absolute paths are returned as-is. Relative paths are resolved
        against self.project_root.

        Args:
            relative_path: A path string from the config.

        Returns:
            Resolved absolute Path.
        """
        p = Path(relative_path)
        if p.is_absolute():
            return p
        return (self.project_root / p).resolve()

    @property
    def skills_dir(self) -> Path:
        """Resolved absolute path to the skills directory."""
        return self.resolve_path(self.paths.skills)

    @property
    def blueprints_dir(self) -> Path:
        """Resolved absolute path to the blueprints directory."""
        return self.resolve_path(self.paths.blueprints)

    @property
    def data_dir(self) -> Path:
        """Resolved absolute path to the data directory."""
        return self.resolve_path(self.paths.data)

    @property
    def logs_dir(self) -> Path:
        """Resolved absolute path to the logs directory."""
        return self.resolve_path(self.paths.logs)

    def get_skill_config(self, skill_name: str) -> dict[str, Any]:
        """Get configuration for a specific skill.

        Returns skill config merged with project-level LLM config as defaults.
        Skill-level config wins over project-level LLM config.

        Args:
            skill_name: The skill's registered name.

        Returns:
            Config dict for the skill, or empty dict if not configured.
        """
        skill_cfg = dict(self.skills.get(skill_name, {}))
        # Project LLM config fills in missing keys — skill config wins
        if self.llm.provider and "llm_provider" not in skill_cfg:
            skill_cfg = {
                "llm_provider": self.llm.provider,
                "llm_model": self.llm.model,
                "llm_api_key": self.llm.api_key,
                **skill_cfg,
            }
        return skill_cfg
