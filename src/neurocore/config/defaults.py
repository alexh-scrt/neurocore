"""Built-in default values for NeuroCore configuration.

These are the lowest-priority defaults. They are overridden by:
neurocore.yaml → .env file → environment variables.
"""

from __future__ import annotations

# --- Project ---
DEFAULT_PROJECT_NAME: str = "my-agent"
DEFAULT_PROJECT_VERSION: str = "0.1.0"

# --- Paths (relative to project root) ---
DEFAULT_SKILLS_DIR: str = "skills"
DEFAULT_BLUEPRINTS_DIR: str = "blueprints"
DEFAULT_DATA_DIR: str = "data"
DEFAULT_LOGS_DIR: str = "logs"

# --- Logging ---
DEFAULT_LOG_LEVEL: str = "INFO"
DEFAULT_LOG_FORMAT: str = "console"

# --- Config file name ---
CONFIG_FILE_NAME: str = "neurocore.yaml"
ENV_FILE_NAME: str = ".env"
ENV_PREFIX: str = "NEUROCORE_"
