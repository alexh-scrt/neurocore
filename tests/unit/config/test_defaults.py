"""Tests for config/defaults.py — verify default constants exist and are sensible."""

from neurocore.config.defaults import (
    CONFIG_FILE_NAME,
    DEFAULT_BLUEPRINTS_DIR,
    DEFAULT_DATA_DIR,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOGS_DIR,
    DEFAULT_PROJECT_NAME,
    DEFAULT_PROJECT_VERSION,
    DEFAULT_SKILLS_DIR,
    ENV_FILE_NAME,
    ENV_PREFIX,
)


def test_config_file_name():
    assert CONFIG_FILE_NAME == "neurocore.yaml"


def test_env_file_name():
    assert ENV_FILE_NAME == ".env"


def test_env_prefix():
    assert ENV_PREFIX == "NEUROCORE_"


def test_default_log_level():
    assert DEFAULT_LOG_LEVEL == "INFO"


def test_default_log_format():
    assert DEFAULT_LOG_FORMAT == "console"


def test_default_paths_are_relative():
    """Default paths should be relative directory names, not absolute."""
    for path in [DEFAULT_SKILLS_DIR, DEFAULT_BLUEPRINTS_DIR, DEFAULT_DATA_DIR, DEFAULT_LOGS_DIR]:
        assert not path.startswith("/"), f"Default path should be relative: {path}"
        assert isinstance(path, str)
