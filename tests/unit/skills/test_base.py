"""T5: Skill base class + SkillMeta tests.

Covers SkillMeta dataclass, Skill lifecycle, config validation,
health checks, error handling, and FlowEngine integration.
"""

from __future__ import annotations

from typing import Any

import pytest
from flowengine import FlowContext

from neurocore.errors import SkillError
from neurocore.skills.base import Skill, SkillMeta


# --- Test fixtures: concrete Skill subclasses ---


class EchoSkill(Skill):
    """Minimal valid Skill for testing."""

    skill_meta = SkillMeta(
        name="echo",
        version="0.1.0",
        description="Echoes input to output",
        provides=["echo_output"],
        consumes=["echo_input"],
        tags=["test", "utility"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        value = context.get("echo_input", "")
        context.set("echo_output", value)
        return context


class ValidatedSkill(Skill):
    """Skill with config_schema for validation testing."""

    skill_meta = SkillMeta(
        name="validated",
        version="1.0.0",
        config_schema={
            "required": ["api_key", "model"],
            "properties": {
                "api_key": {"type": "string"},
                "model": {"type": "string"},
                "max_retries": {"type": "integer"},
                "temperature": {"type": "number"},
                "verbose": {"type": "boolean"},
            },
        },
    )

    def process(self, context: FlowContext) -> FlowContext:
        return context


class NoMetaSkill(Skill):
    """Skill without skill_meta — should fail."""

    def process(self, context: FlowContext) -> FlowContext:
        return context


# Remove the class attribute so it's truly missing
if hasattr(NoMetaSkill, "skill_meta"):
    delattr(NoMetaSkill, "skill_meta")


class BadMetaSkill(Skill):
    """Skill with invalid skill_meta type."""

    skill_meta = {"name": "bad", "version": "0.1.0"}  # type: ignore[assignment]

    def process(self, context: FlowContext) -> FlowContext:
        return context


class AsyncEchoSkill(Skill):
    """Skill with async processing."""

    skill_meta = SkillMeta(name="async-echo", version="0.1.0")

    def process(self, context: FlowContext) -> FlowContext:
        return context

    async def process_async(self, context: FlowContext) -> FlowContext:
        value = context.get("input", "")
        context.set("output", f"async:{value}")
        return context


# --- SkillMeta tests ---


class TestSkillMeta:
    def test_required_fields(self):
        meta = SkillMeta(name="test", version="0.1.0")
        assert meta.name == "test"
        assert meta.version == "0.1.0"

    def test_defaults(self):
        meta = SkillMeta(name="test", version="0.1.0")
        assert meta.description == ""
        assert meta.author == ""
        assert meta.requires == []
        assert meta.provides == []
        assert meta.consumes == []
        assert meta.config_schema == {}
        assert meta.tags == []

    def test_full_metadata(self):
        meta = SkillMeta(
            name="neuroweave",
            version="0.1.0",
            description="Knowledge graph memory",
            author="NeuroWeave Team",
            requires=["anthropic>=0.42", "networkx>=3.2"],
            provides=["knowledge_context"],
            consumes=["user_message"],
            config_schema={"required": ["llm_api_key"]},
            tags=["memory", "graph", "llm"],
        )
        assert meta.name == "neuroweave"
        assert len(meta.requires) == 2
        assert "memory" in meta.tags

    def test_frozen_immutable(self):
        meta = SkillMeta(name="test", version="0.1.0")
        with pytest.raises(AttributeError):
            meta.name = "changed"  # type: ignore[misc]

    def test_equality(self):
        meta1 = SkillMeta(name="test", version="0.1.0")
        meta2 = SkillMeta(name="test", version="0.1.0")
        assert meta1 == meta2

    def test_inequality(self):
        meta1 = SkillMeta(name="test", version="0.1.0")
        meta2 = SkillMeta(name="test", version="0.2.0")
        assert meta1 != meta2


# --- Skill instantiation tests ---


class TestSkillInit:
    def test_default_name_from_meta(self):
        skill = EchoSkill()
        assert skill.name == "echo"

    def test_custom_name_override(self):
        skill = EchoSkill(name="custom-echo")
        assert skill.name == "custom-echo"

    def test_no_meta_raises_skill_error(self):
        with pytest.raises(SkillError, match="must define 'skill_meta'"):
            NoMetaSkill()

    def test_bad_meta_type_raises_skill_error(self):
        with pytest.raises(SkillError, match="must be a SkillMeta instance"):
            BadMetaSkill()

    def test_meta_accessible(self):
        skill = EchoSkill()
        assert skill.skill_meta.name == "echo"
        assert skill.skill_meta.version == "0.1.0"


# --- Skill lifecycle tests ---


class TestSkillLifecycle:
    def test_not_initialized_before_init(self):
        skill = EchoSkill()
        assert not skill.is_initialized

    def test_initialized_after_init(self):
        skill = EchoSkill()
        skill.init({})
        assert skill.is_initialized

    def test_config_stored_after_init(self):
        skill = EchoSkill()
        skill.init({"key": "value"})
        assert skill.config == {"key": "value"}

    def test_process_returns_context(self):
        skill = EchoSkill()
        skill.init({})
        ctx = FlowContext()
        ctx.set("echo_input", "hello")
        result = skill.process(ctx)
        assert result.get("echo_output") == "hello"

    def test_setup_and_teardown_callable(self):
        skill = EchoSkill()
        skill.init({})
        ctx = FlowContext()
        # Should not raise
        skill.setup(ctx)
        skill.teardown(ctx)


# --- Config validation tests ---


class TestValidateConfig:
    def test_valid_config_no_errors(self):
        skill = ValidatedSkill()
        skill.init({"api_key": "sk-123", "model": "gpt-4", "max_retries": 3})
        errors = skill.validate_config()
        assert errors == []

    def test_missing_required_key(self):
        skill = ValidatedSkill()
        skill.init({"api_key": "sk-123"})  # Missing 'model'
        errors = skill.validate_config()
        assert any("model" in e for e in errors)

    def test_wrong_type_detected(self):
        skill = ValidatedSkill()
        skill.init({"api_key": "sk-123", "model": "gpt-4", "max_retries": "not-an-int"})
        errors = skill.validate_config()
        assert any("max_retries" in e and "integer" in e for e in errors)

    def test_boolean_not_confused_with_integer(self):
        skill = ValidatedSkill()
        skill.init({"api_key": "sk-123", "model": "gpt-4", "max_retries": True})
        errors = skill.validate_config()
        assert any("max_retries" in e for e in errors)

    def test_number_type_accepts_int_and_float(self):
        skill = ValidatedSkill()
        skill.init({"api_key": "k", "model": "m", "temperature": 0.7})
        errors = skill.validate_config()
        assert not any("temperature" in e for e in errors)

        skill2 = ValidatedSkill()
        skill2.init({"api_key": "k", "model": "m", "temperature": 1})
        errors2 = skill2.validate_config()
        assert not any("temperature" in e for e in errors2)

    def test_no_schema_no_errors(self):
        skill = EchoSkill()
        skill.init({"anything": "goes"})
        errors = skill.validate_config()
        assert errors == []


# --- Health check tests ---


class TestHealthCheck:
    def test_healthy_after_init(self):
        skill = EchoSkill()
        skill.init({})
        assert skill.health_check() is True

    def test_unhealthy_before_init(self):
        skill = EchoSkill()
        assert skill.health_check() is False


# --- Async support tests ---


class TestAsyncSkill:
    def test_is_async_property(self):
        skill = AsyncEchoSkill()
        assert skill.is_async is True

    def test_sync_skill_not_async(self):
        skill = EchoSkill()
        assert skill.is_async is False


# --- Repr tests ---


class TestRepr:
    def test_repr_with_meta(self):
        skill = EchoSkill()
        r = repr(skill)
        assert "EchoSkill" in r
        assert "echo" in r
        assert "0.1.0" in r

    def test_repr_custom_name(self):
        skill = EchoSkill(name="my-echo")
        r = repr(skill)
        assert "my-echo" in r


# --- Top-level import tests ---


class TestImports:
    def test_import_from_skills_package(self):
        from neurocore.skills import Skill, SkillMeta

        assert Skill is not None
        assert SkillMeta is not None

    def test_import_from_top_level(self):
        from neurocore import Skill, SkillMeta

        assert Skill is not None
        assert SkillMeta is not None
