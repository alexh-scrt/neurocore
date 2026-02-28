"""Shared test fixtures for NeuroCore."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory with minimal structure."""
    (tmp_path / "skills").mkdir()
    (tmp_path / "blueprints").mkdir()
    return tmp_path


@pytest.fixture
def env_override():
    """Context manager to temporarily set environment variables."""
    original: dict[str, str | None] = {}

    def _set(**kwargs: str | None) -> None:
        for key, value in kwargs.items():
            original[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    yield _set

    # Restore original values
    for key, value in original.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
