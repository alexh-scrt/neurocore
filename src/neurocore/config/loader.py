"""Configuration loader for NeuroCore.

Loads configuration with the following priority (highest wins):
    1. Environment variables (``NEUROCORE_`` prefix, double underscore for nesting)
    2. .env file (project root)
    3. neurocore.yaml
    4. Built-in defaults

Usage::

    from neurocore.config import load_config

    # Auto-detect project root (walks up from cwd)
    config = load_config()

    # Explicit project root
    config = load_config(project_root=Path("/path/to/project"))

    # Explicit config file
    config = load_config(config_path=Path("custom-config.yaml"))
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from neurocore.config.defaults import CONFIG_FILE_NAME, ENV_FILE_NAME, ENV_PREFIX
from neurocore.config.schema import NeuroCoreConfig
from neurocore.errors import ConfigError


def find_project_root(start: Path | None = None) -> Path | None:
    """Walk up from `start` looking for neurocore.yaml.

    Args:
        start: Directory to begin searching from. Defaults to cwd.

    Returns:
        The directory containing neurocore.yaml, or None if not found.
    """
    current = (start or Path.cwd()).resolve()
    while True:
        if (current / CONFIG_FILE_NAME).is_file():
            return current
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            return None
        current = parent


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed dict (empty dict if file is empty).

    Raises:
        ConfigError: If the file cannot be read or parsed.
    """
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}")
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}")


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Apply ``NEUROCORE_`` environment variable overrides into the config dict.

    Supports nested keys via double underscore:
        NEUROCORE_LOGGING__LEVEL=DEBUG  →  data["logging"]["level"] = "DEBUG"
        NEUROCORE_PROJECT__NAME=foo     →  data["project"]["name"] = "foo"

    Only applies to known top-level sections (project, paths, logging).
    Skills env vars are handled separately.

    Args:
        data: The config dict to update (mutated in place).

    Returns:
        The updated config dict.
    """
    prefix = ENV_PREFIX.upper()
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue

        # Strip prefix and split on double underscore
        remainder = key[len(prefix):]
        parts = [p.lower() for p in remainder.split("__")]

        if not parts:
            continue

        # Walk into the nested dict, creating intermediate dicts as needed
        target = data
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            if isinstance(target[part], dict):
                target = target[part]
            else:
                # Can't nest into a non-dict value
                break
        else:
            target[parts[-1]] = value

    return data


def load_config(
    project_root: Path | None = None,
    config_path: Path | None = None,
) -> NeuroCoreConfig:
    """Load NeuroCore configuration.

    Priority (highest wins):
        1. Environment variables (NEUROCORE_*)
        2. .env file
        3. neurocore.yaml
        4. Built-in defaults (in schema.py)

    Args:
        project_root: Explicit project root directory.
            If not provided, walks up from cwd looking for neurocore.yaml.
        config_path: Explicit path to a config YAML file.
            If provided, project_root defaults to its parent directory.

    Returns:
        Fully resolved NeuroCoreConfig.

    Raises:
        ConfigError: If config file is specified but invalid.
    """
    # Determine project root and config path
    if config_path is not None:
        config_path = Path(config_path).resolve()
        root = project_root or config_path.parent
    elif project_root is not None:
        root = Path(project_root).resolve()
        config_path = root / CONFIG_FILE_NAME
    else:
        root = find_project_root()
        if root is not None:
            config_path = root / CONFIG_FILE_NAME
        else:
            # No neurocore.yaml found — use defaults with cwd as root
            root = Path.cwd().resolve()
            config_path = None

    root = Path(root).resolve()

    # Load .env file (if it exists)
    env_path = root / ENV_FILE_NAME
    if env_path.is_file():
        load_dotenv(env_path, override=True)

    # Load YAML config (or start with empty dict for defaults)
    if config_path is not None and config_path.is_file():
        data = _load_yaml(config_path)
    else:
        data = {}

    # Apply environment variable overrides
    _apply_env_overrides(data)

    # Set project_root in the data
    data["project_root"] = root

    # Build and return the config model (pydantic handles defaults)
    try:
        return NeuroCoreConfig(**data)
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}")
