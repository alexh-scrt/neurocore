"""Skill discovery — directory scan + entry points.

Two discovery mechanisms, merged into a unified SkillRegistry:

1. **Directory scan** — walks a skills/ directory, imports .py files,
   finds Skill subclasses.
2. **Entry points** — scans the `neurocore.skills` group from installed
   packages (pyproject.toml [project.entry-points."neurocore.skills"]).

Entry points take precedence — a pip-installed skill wins over a
local copy with the same name.

Usage:
    from neurocore.skills.loader import discover_skills
    from neurocore.config import load_config

    config = load_config()
    registry = discover_skills(config)
    print(registry.list_skills())
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
from importlib.metadata import entry_points
from pathlib import Path
from typing import TYPE_CHECKING

from neurocore.errors import SkillError
from neurocore.skills.base import Skill, SkillMeta
from neurocore.skills.registry import SkillRegistry

if TYPE_CHECKING:
    from neurocore.config.schema import NeuroCoreConfig

# Entry point group name for skill discovery
ENTRY_POINT_GROUP = "neurocore.skills"


def discover_directory(
    skills_dir: Path,
    *,
    registry: SkillRegistry | None = None,
) -> SkillRegistry:
    """Discover skills by scanning a directory for .py files.

    Walks the directory (non-recursive by default), imports each .py
    file as a module, and finds all Skill subclasses with valid
    skill_meta.

    Args:
        skills_dir: Path to the skills directory.
        registry: Existing registry to add to. Creates a new one if None.

    Returns:
        SkillRegistry with discovered skills.

    Raises:
        SkillError: If a skill file cannot be imported (logged, not fatal).
    """
    if registry is None:
        registry = SkillRegistry()

    if not skills_dir.is_dir():
        return registry

    for py_file in sorted(skills_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue  # Skip __init__.py, __pycache__, _private.py

        skill_classes = _import_skills_from_file(py_file)
        for skill_class in skill_classes:
            try:
                registry.register(skill_class)
            except SkillError:
                # Duplicate name — skip silently (entry points will override)
                pass

    return registry


def _import_skills_from_file(file_path: Path) -> list[type[Skill]]:
    """Import a Python file and extract Skill subclasses.

    Args:
        file_path: Path to the .py file.

    Returns:
        List of Skill subclasses found in the file.

    Raises:
        SkillError: If the file cannot be imported.
    """
    module_name = f"neurocore_skills.{file_path.stem}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise SkillError(f"Cannot create module spec for {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as e:
        # Clean up sys.modules on failure
        sys.modules.pop(module_name, None)
        raise SkillError(f"Failed to import skill file {file_path}: {e}") from e

    # Find all Skill subclasses defined in this module
    skills: list[type[Skill]] = []
    for _name, obj in inspect.getmembers(module, inspect.isclass):
        if (
            issubclass(obj, Skill)
            and obj is not Skill
            and obj.__module__ == module_name
            and hasattr(obj, "skill_meta")
            and isinstance(obj.skill_meta, SkillMeta)
        ):
            skills.append(obj)

    return skills


def discover_entry_points(
    *,
    registry: SkillRegistry | None = None,
) -> SkillRegistry:
    """Discover skills from installed package entry points.

    Scans the `neurocore.skills` entry point group. Each entry point
    should point to a Skill subclass.

    Entry point format in pyproject.toml:
        [project.entry-points."neurocore.skills"]
        neuroweave = "neurocore_skill_neuroweave:NeuroWeaveSkill"

    Args:
        registry: Existing registry to add to. Creates a new one if None.

    Returns:
        SkillRegistry with discovered skills.
    """
    if registry is None:
        registry = SkillRegistry()

    eps = entry_points(group=ENTRY_POINT_GROUP)

    for ep in eps:
        try:
            skill_class = ep.load()
        except Exception:
            # Failed to load entry point — skip
            continue

        if (
            isinstance(skill_class, type)
            and issubclass(skill_class, Skill)
            and hasattr(skill_class, "skill_meta")
            and isinstance(skill_class.skill_meta, SkillMeta)
        ):
            try:
                # Entry points get replace=True precedence
                registry.register(skill_class, replace=True)
            except SkillError:
                pass

    return registry


def discover_skills(
    config: NeuroCoreConfig,
    *,
    registry: SkillRegistry | None = None,
) -> SkillRegistry:
    """Discover all skills — directory scan + entry points.

    Discovery order:
    1. Directory scan (skills/ folder) — baseline
    2. Entry points (pip-installed packages) — override duplicates

    This means entry-point skills take precedence over local skills
    with the same name.

    Args:
        config: NeuroCoreConfig with skills_dir path.
        registry: Existing registry to add to. Creates a new one if None.

    Returns:
        SkillRegistry with all discovered skills.
    """
    if registry is None:
        registry = SkillRegistry()

    # Phase 0: Built-in skills (always available; overridable by user skills)
    _register_builtins(registry)

    # Phase 1: Directory scan (lower priority)
    discover_directory(config.skills_dir, registry=registry)

    # Phase 2: Entry points (higher priority — replace=True)
    discover_entry_points(registry=registry)

    return registry


def _register_builtins(registry: SkillRegistry) -> None:
    """Register NeuroCore's built-in skills (e.g. the approval gate)."""
    import contextlib

    from neurocore.skills.builtin import BUILTIN_SKILLS

    for skill_class in BUILTIN_SKILLS:
        with contextlib.suppress(SkillError):
            registry.register(skill_class, replace=True)
