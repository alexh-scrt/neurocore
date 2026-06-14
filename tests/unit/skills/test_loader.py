"""T6+T7: Skill discovery tests — directory scan, entry points, merge.

Creates temporary skill files on disk to test the full discovery pipeline.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flowengine import FlowContext

from neurocore.config.schema import NeuroCoreConfig, PathsConfig
from neurocore.errors import SkillError
from neurocore.skills.base import Skill, SkillMeta
from neurocore.skills.loader import (
    _import_skills_from_file,
    discover_directory,
    discover_entry_points,
    discover_skills,
)
from neurocore.skills.registry import SkillRegistry

from neurocore.skills.builtin import BUILTIN_SKILLS

BUILTIN_NAMES = {s.skill_meta.name for s in BUILTIN_SKILLS}


def _non_builtin_count(registry: SkillRegistry) -> int:
    """Count of discovered skills excluding always-registered built-ins."""
    return len(set(registry.list_skills()) - BUILTIN_NAMES)


# --- Helpers: create skill files on disk ---

ECHO_SKILL_CODE = '''\
"""Echo skill for testing."""
from flowengine import FlowContext
from neurocore.skills import Skill, SkillMeta


class EchoSkill(Skill):
    skill_meta = SkillMeta(
        name="echo",
        version="0.1.0",
        description="Echoes input",
        provides=["echo_output"],
        consumes=["echo_input"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        context.set("echo_output", context.get("echo_input", ""))
        return context
'''

UPPERCASE_SKILL_CODE = '''\
"""Uppercase skill for testing."""
from flowengine import FlowContext
from neurocore.skills import Skill, SkillMeta


class UppercaseSkill(Skill):
    skill_meta = SkillMeta(
        name="uppercase",
        version="0.1.0",
        description="Uppercases input",
    )

    def process(self, context: FlowContext) -> FlowContext:
        return context
'''

NO_SKILL_CODE = '''\
"""Utility module with no Skill subclasses."""

def helper():
    return 42
'''

BAD_IMPORT_CODE = '''\
"""Module that fails to import."""
import nonexistent_module_xyz_123
'''

MULTI_SKILL_CODE = '''\
"""Module with multiple skills."""
from flowengine import FlowContext
from neurocore.skills import Skill, SkillMeta


class FirstSkill(Skill):
    skill_meta = SkillMeta(name="first", version="0.1.0")

    def process(self, context: FlowContext) -> FlowContext:
        return context


class SecondSkill(Skill):
    skill_meta = SkillMeta(name="second", version="0.1.0")

    def process(self, context: FlowContext) -> FlowContext:
        return context
'''


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    """Create a temporary skills directory with test skill files."""
    d = tmp_path / "skills"
    d.mkdir()
    return d


# --- T6: Directory scan tests ---


class TestDiscoverDirectory:
    def test_discovers_single_skill(self, skills_dir: Path):
        (skills_dir / "echo.py").write_text(ECHO_SKILL_CODE)
        registry = discover_directory(skills_dir)
        assert "echo" in registry
        assert len(registry) == 1

    def test_discovers_multiple_files(self, skills_dir: Path):
        (skills_dir / "echo.py").write_text(ECHO_SKILL_CODE)
        (skills_dir / "uppercase.py").write_text(UPPERCASE_SKILL_CODE)
        registry = discover_directory(skills_dir)
        assert "echo" in registry
        assert "uppercase" in registry
        assert len(registry) == 2

    def test_discovers_multiple_skills_in_one_file(self, skills_dir: Path):
        (skills_dir / "multi.py").write_text(MULTI_SKILL_CODE)
        registry = discover_directory(skills_dir)
        assert "first" in registry
        assert "second" in registry
        assert len(registry) == 2

    def test_skips_underscore_files(self, skills_dir: Path):
        (skills_dir / "__init__.py").write_text(ECHO_SKILL_CODE)
        (skills_dir / "_private.py").write_text(UPPERCASE_SKILL_CODE)
        registry = discover_directory(skills_dir)
        assert len(registry) == 0

    def test_skips_files_without_skills(self, skills_dir: Path):
        (skills_dir / "utils.py").write_text(NO_SKILL_CODE)
        registry = discover_directory(skills_dir)
        assert len(registry) == 0

    def test_nonexistent_directory_returns_empty(self, tmp_path: Path):
        registry = discover_directory(tmp_path / "nonexistent")
        assert len(registry) == 0

    def test_import_error_raises(self, skills_dir: Path):
        (skills_dir / "bad.py").write_text(BAD_IMPORT_CODE)
        # _import_skills_from_file raises, but discover_directory
        # catches SkillError for duplicate names. Let's test the
        # underlying import directly.
        with pytest.raises(SkillError, match="Failed to import"):
            _import_skills_from_file(skills_dir / "bad.py")

    def test_adds_to_existing_registry(self, skills_dir: Path):
        (skills_dir / "echo.py").write_text(ECHO_SKILL_CODE)

        # Pre-populate registry
        reg = SkillRegistry()

        class PreExistingSkill(Skill):
            skill_meta = SkillMeta(name="pre", version="0.1.0")
            def process(self, context: FlowContext) -> FlowContext:
                return context

        reg.register(PreExistingSkill)

        discover_directory(skills_dir, registry=reg)
        assert "pre" in reg
        assert "echo" in reg
        assert len(reg) == 2

    def test_duplicate_names_across_files_skipped(self, skills_dir: Path):
        """If two files define skills with the same name, first wins."""
        (skills_dir / "aaa_echo.py").write_text(ECHO_SKILL_CODE)
        # Create another file with same skill name
        code2 = ECHO_SKILL_CODE.replace("class EchoSkill", "class EchoSkill2")
        (skills_dir / "bbb_echo2.py").write_text(code2)
        registry = discover_directory(skills_dir)
        # First file (aaa_) wins, second silently skipped
        assert "echo" in registry
        assert len(registry) == 1

    def test_discovered_skill_is_functional(self, skills_dir: Path):
        (skills_dir / "echo.py").write_text(ECHO_SKILL_CODE)
        registry = discover_directory(skills_dir)
        instance = registry.create("echo")
        instance.init({})
        ctx = FlowContext()
        ctx.set("echo_input", "hello")
        result = instance.process(ctx)
        assert result.get("echo_output") == "hello"


# --- T7: Entry point discovery tests ---


class TestDiscoverEntryPoints:
    def test_discovers_from_entry_points(self):
        """Mock entry points to simulate installed skill packages."""

        class EPSkill(Skill):
            skill_meta = SkillMeta(name="ep-skill", version="1.0.0")
            def process(self, context: FlowContext) -> FlowContext:
                return context

        mock_ep = MagicMock()
        mock_ep.load.return_value = EPSkill

        with patch("neurocore.skills.loader.entry_points", return_value=[mock_ep]):
            registry = discover_entry_points()

        assert "ep-skill" in registry

    def test_entry_point_load_failure_skipped(self):
        """If an entry point fails to load, it's skipped."""
        mock_ep = MagicMock()
        mock_ep.load.side_effect = ImportError("package not found")

        with patch("neurocore.skills.loader.entry_points", return_value=[mock_ep]):
            registry = discover_entry_points()

        assert len(registry) == 0

    def test_entry_point_non_skill_skipped(self):
        """If an entry point loads something that's not a Skill, skip it."""
        mock_ep = MagicMock()
        mock_ep.load.return_value = str  # Not a Skill

        with patch("neurocore.skills.loader.entry_points", return_value=[mock_ep]):
            registry = discover_entry_points()

        assert len(registry) == 0

    def test_entry_points_add_to_existing_registry(self):
        class EPSkill(Skill):
            skill_meta = SkillMeta(name="ep-skill", version="1.0.0")
            def process(self, context: FlowContext) -> FlowContext:
                return context

        mock_ep = MagicMock()
        mock_ep.load.return_value = EPSkill

        reg = SkillRegistry()

        class LocalSkill(Skill):
            skill_meta = SkillMeta(name="local", version="0.1.0")
            def process(self, context: FlowContext) -> FlowContext:
                return context

        reg.register(LocalSkill)

        with patch("neurocore.skills.loader.entry_points", return_value=[mock_ep]):
            discover_entry_points(registry=reg)

        assert "local" in reg
        assert "ep-skill" in reg


# --- T7: Merge / precedence tests ---


class TestDiscoverSkills:
    def test_merges_directory_and_entry_points(self, skills_dir: Path):
        (skills_dir / "echo.py").write_text(ECHO_SKILL_CODE)

        class EPSkill(Skill):
            skill_meta = SkillMeta(name="ep-skill", version="1.0.0")
            def process(self, context: FlowContext) -> FlowContext:
                return context

        mock_ep = MagicMock()
        mock_ep.load.return_value = EPSkill

        config = NeuroCoreConfig(
            paths=PathsConfig(skills=str(skills_dir)),
            project_root=skills_dir.parent,
        )

        with patch("neurocore.skills.loader.entry_points", return_value=[mock_ep]):
            registry = discover_skills(config)

        assert "echo" in registry
        assert "ep-skill" in registry
        assert _non_builtin_count(registry) == 2

    def test_entry_point_overrides_directory(self, skills_dir: Path):
        """Entry point skill with same name replaces directory skill."""
        (skills_dir / "echo.py").write_text(ECHO_SKILL_CODE)

        class EPEchoSkill(Skill):
            skill_meta = SkillMeta(name="echo", version="2.0.0")
            def process(self, context: FlowContext) -> FlowContext:
                context.set("echo_output", "from-entry-point")
                return context

        mock_ep = MagicMock()
        mock_ep.load.return_value = EPEchoSkill

        config = NeuroCoreConfig(
            paths=PathsConfig(skills=str(skills_dir)),
            project_root=skills_dir.parent,
        )

        with patch("neurocore.skills.loader.entry_points", return_value=[mock_ep]):
            registry = discover_skills(config)

        # Entry point version wins
        assert registry.get("echo") is EPEchoSkill
        assert registry.get("echo").skill_meta.version == "2.0.0"

    def test_empty_directory_and_no_entry_points(self, tmp_path: Path):
        config = NeuroCoreConfig(
            paths=PathsConfig(skills="skills"),
            project_root=tmp_path,
        )

        with patch("neurocore.skills.loader.entry_points", return_value=[]):
            registry = discover_skills(config)

        assert _non_builtin_count(registry) == 0

    def test_passes_existing_registry(self, skills_dir: Path):
        (skills_dir / "echo.py").write_text(ECHO_SKILL_CODE)

        reg = SkillRegistry()

        class PreExistingSkill(Skill):
            skill_meta = SkillMeta(name="pre", version="0.1.0")
            def process(self, context: FlowContext) -> FlowContext:
                return context

        reg.register(PreExistingSkill)

        config = NeuroCoreConfig(
            paths=PathsConfig(skills=str(skills_dir)),
            project_root=skills_dir.parent,
        )

        with patch("neurocore.skills.loader.entry_points", return_value=[]):
            result = discover_skills(config, registry=reg)

        assert "pre" in result
        assert "echo" in result
        assert result is reg  # Same registry object


# --- Import tests ---


class TestImports:
    def test_import_from_skills_package(self):
        from neurocore.skills import (
            SkillRegistry,
            discover_directory,
            discover_entry_points,
            discover_skills,
        )

        assert SkillRegistry is not None
        assert discover_directory is not None
        assert discover_entry_points is not None
        assert discover_skills is not None
