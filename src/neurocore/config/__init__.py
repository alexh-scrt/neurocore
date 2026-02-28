"""NeuroCore configuration system.

Handles YAML config loading, .env overlay, environment variable
overrides, and path resolution.

Usage:
    from neurocore.config import load_config, NeuroCoreConfig

    config = load_config()  # auto-detects neurocore.yaml
    print(config.project.name)
    print(config.skills_dir)
"""

from neurocore.config.loader import find_project_root, load_config
from neurocore.config.schema import (
    LogFormat,
    LogLevel,
    LoggingConfig,
    NeuroCoreConfig,
    PathsConfig,
    ProjectConfig,
)

__all__ = [
    "find_project_root",
    "load_config",
    "LogFormat",
    "LogLevel",
    "LoggingConfig",
    "NeuroCoreConfig",
    "PathsConfig",
    "ProjectConfig",
]
