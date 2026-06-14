"""Construct a RunStore from NeuroCoreConfig."""
from __future__ import annotations

from neurocore.config.schema import NeuroCoreConfig
from neurocore.errors import ConfigError
from neurocore.persistence.base import RunStore
from neurocore.persistence.memory_store import InMemoryRunStore
from neurocore.persistence.sqlite_store import SQLiteRunStore


def build_run_store(config: NeuroCoreConfig) -> RunStore | None:
    """Build a RunStore from config, or None when persistence is disabled.

    Args:
        config: Project configuration.

    Returns:
        A RunStore instance, or None if ``persistence.enabled`` is False.

    Raises:
        ConfigError: If the configured backend is unknown.
    """
    if not config.persistence.enabled:
        return None
    backend = config.persistence.backend
    if backend == "memory":
        return InMemoryRunStore()
    if backend == "sqlite":
        return SQLiteRunStore(config.runs_db_path)
    raise ConfigError(
        f"Unknown persistence backend: {backend!r}. Expected: sqlite | memory."
    )
