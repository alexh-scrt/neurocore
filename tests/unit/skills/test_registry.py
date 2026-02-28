"""T6: SkillRegistry tests — registration, lookup, creation, edge cases."""

from __future__ import annotations

import pytest
from flowengine import FlowContext

from neurocore.errors import SkillError
from neurocore.skills.base import Skill, SkillMeta
from neurocore.skills.registry import SkillRegistry


# --- Test skill classes ---


class AlphaSkill(Skill):
    skill_meta = SkillMeta(name="alpha", version="1.0.0", description="Alpha skill")

    def process(self, context: FlowContext) -> FlowContext:
        return context


class BetaSkill(Skill):
    skill_meta = SkillMeta(
        name="beta",
        version="2.0.0",
        tags=["test"],
        provides=["beta_output"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        return context


class DuplicateAlphaSkill(Skill):
    """Another skill with name='alpha' — should conflict."""

    skill_meta = SkillMeta(name="alpha", version="0.9.0")

    def process(self, context: FlowContext) -> FlowContext:
        return context


# --- Registration tests ---


class TestRegister:
    def test_register_skill(self):
        reg = SkillRegistry()
        reg.register(AlphaSkill)
        assert "alpha" in reg

    def test_register_multiple(self):
        reg = SkillRegistry()
        reg.register(AlphaSkill)
        reg.register(BetaSkill)
        assert len(reg) == 2

    def test_duplicate_name_raises(self):
        reg = SkillRegistry()
        reg.register(AlphaSkill)
        with pytest.raises(SkillError, match="already registered"):
            reg.register(DuplicateAlphaSkill)

    def test_duplicate_with_replace(self):
        reg = SkillRegistry()
        reg.register(AlphaSkill)
        reg.register(DuplicateAlphaSkill, replace=True)
        cls = reg.get("alpha")
        assert cls is DuplicateAlphaSkill

    def test_register_non_skill_raises(self):
        reg = SkillRegistry()
        with pytest.raises(SkillError, match="not a Skill subclass"):
            reg.register(str)  # type: ignore[arg-type]

    def test_register_class_without_meta_raises(self):
        class BadSkill(Skill):
            def process(self, context: FlowContext) -> FlowContext:
                return context

        if hasattr(BadSkill, "skill_meta"):
            delattr(BadSkill, "skill_meta")

        reg = SkillRegistry()
        with pytest.raises(SkillError, match="missing or invalid"):
            reg.register(BadSkill)


# --- Lookup tests ---


class TestLookup:
    def test_get_existing(self):
        reg = SkillRegistry()
        reg.register(AlphaSkill)
        assert reg.get("alpha") is AlphaSkill

    def test_get_missing_returns_none(self):
        reg = SkillRegistry()
        assert reg.get("nonexistent") is None

    def test_get_or_raise_existing(self):
        reg = SkillRegistry()
        reg.register(AlphaSkill)
        assert reg.get_or_raise("alpha") is AlphaSkill

    def test_get_or_raise_missing(self):
        reg = SkillRegistry()
        reg.register(BetaSkill)
        with pytest.raises(SkillError, match="not found.*Available.*beta"):
            reg.get_or_raise("nonexistent")

    def test_contains(self):
        reg = SkillRegistry()
        reg.register(AlphaSkill)
        assert "alpha" in reg
        assert "beta" not in reg


# --- List tests ---


class TestList:
    def test_list_skills_sorted(self):
        reg = SkillRegistry()
        reg.register(BetaSkill)
        reg.register(AlphaSkill)
        assert reg.list_skills() == ["alpha", "beta"]

    def test_list_skills_empty(self):
        reg = SkillRegistry()
        assert reg.list_skills() == []

    def test_list_skill_metas(self):
        reg = SkillRegistry()
        reg.register(AlphaSkill)
        reg.register(BetaSkill)
        metas = reg.list_skill_metas()
        assert len(metas) == 2
        assert metas[0].name == "alpha"
        assert metas[1].name == "beta"


# --- Create tests ---


class TestCreate:
    def test_create_default_name(self):
        reg = SkillRegistry()
        reg.register(AlphaSkill)
        instance = reg.create("alpha")
        assert isinstance(instance, AlphaSkill)
        assert instance.name == "alpha"

    def test_create_custom_name(self):
        reg = SkillRegistry()
        reg.register(AlphaSkill)
        instance = reg.create("alpha", instance_name="my-alpha")
        assert instance.name == "my-alpha"

    def test_create_missing_raises(self):
        reg = SkillRegistry()
        with pytest.raises(SkillError, match="not found"):
            reg.create("nonexistent")


# --- Repr / len tests ---


class TestMisc:
    def test_len(self):
        reg = SkillRegistry()
        assert len(reg) == 0
        reg.register(AlphaSkill)
        assert len(reg) == 1

    def test_repr(self):
        reg = SkillRegistry()
        reg.register(AlphaSkill)
        reg.register(BetaSkill)
        r = repr(reg)
        assert "alpha" in r
        assert "beta" in r
