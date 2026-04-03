"""Tests for NC-004 — LLM Provider Protocol."""

import pytest
from flowengine import FlowContext

from neurocore import AsyncSkill, Skill, SkillMeta
from neurocore.config.schema import NeuroCoreConfig
from neurocore.errors import BlueprintError
from neurocore.llm.provider import (
    LLMMessage,
    LLMProvider,
    MockProvider,
    build_provider,
)
from neurocore.runtime.blueprint import Blueprint, BlueprintComponent, FlowDefinition, FlowStep
from neurocore.runtime.executor import execute_blueprint
from neurocore.skills.registry import SkillRegistry


async def test_mock_provider_returns_queued_response():
    provider = MockProvider()
    provider.set_response("hello world")
    result = await provider.complete([LLMMessage(role="user", content="hi")])
    assert result.content == "hello world"


async def test_mock_provider_increments_call_count():
    provider = MockProvider()
    await provider.complete([LLMMessage(role="user", content="hi")])
    await provider.complete([LLMMessage(role="user", content="hi")])
    assert provider.call_count == 2


async def test_mock_provider_returns_default_when_queue_empty():
    provider = MockProvider()
    result = await provider.complete([LLMMessage(role="user", content="hi")])
    assert result.content == "mock response"


async def test_mock_provider_stream_yields_characters():
    provider = MockProvider()
    provider.set_response("abc")
    chars = []
    async for c in provider.stream([LLMMessage(role="user", content="hi")]):
        chars.append(c)
    assert "".join(chars) == "abc"


def test_build_provider_returns_none_when_no_llm_provider_key():
    assert build_provider({}) is None
    assert build_provider({"llm_model": "gpt-4o"}) is None


def test_build_provider_mock():
    provider = build_provider({"llm_provider": "mock", "llm_model": "test-model"})
    assert provider is not None
    assert provider.provider_name == "mock"
    assert provider.model == "test-model"


def test_build_provider_unknown_raises_value_error():
    with pytest.raises(ValueError, match="Unknown llm_provider"):
        build_provider({"llm_provider": "foobar"})


def test_llm_provider_protocol_satisfied_by_mock():
    provider = MockProvider()
    assert isinstance(provider, LLMProvider)


class LLMSkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="llm-skill",
        version="0.1.0",
        requires_llm=True,
        provides=["llm_output"],
    )

    async def process(self, context: FlowContext) -> FlowContext:
        assert self.llm is not None
        result = await self.llm.complete([LLMMessage(role="user", content="hi")])
        context.set("llm_output", result.content)
        return context


class NoLLMSkill(Skill):
    skill_meta = SkillMeta(name="no-llm", version="0.1.0", provides=["output"])

    def process(self, context: FlowContext) -> FlowContext:
        context.set("output", "done")
        return context


def test_skill_llm_injected_when_requires_llm_true():
    registry = SkillRegistry()
    registry.register(LLMSkill)

    bp = Blueprint(
        name="llm-test",
        version="1.0",
        components=[
            BlueprintComponent(
                name="llm",
                type="llm-skill",
                config={"llm_provider": "mock"},
            )
        ],
        flow=FlowDefinition(
            type="sequential",
            steps=[FlowStep(component="llm")],
        ),
    )

    result = execute_blueprint(bp, registry, NeuroCoreConfig())
    assert result.get("llm_output") == "mock response"


def test_skill_llm_none_when_requires_llm_false():
    registry = SkillRegistry()
    registry.register(NoLLMSkill)

    bp = Blueprint(
        name="no-llm-test",
        version="1.0",
        components=[BlueprintComponent(name="nollm", type="no-llm")],
        flow=FlowDefinition(
            type="sequential",
            steps=[FlowStep(component="nollm")],
        ),
    )

    result = execute_blueprint(bp, registry, NeuroCoreConfig())
    assert result.get("output") == "done"


def test_requires_llm_true_without_config_raises_blueprint_error():
    registry = SkillRegistry()
    registry.register(LLMSkill)

    bp = Blueprint(
        name="no-provider",
        version="1.0",
        components=[BlueprintComponent(name="llm", type="llm-skill")],
        flow=FlowDefinition(
            type="sequential",
            steps=[FlowStep(component="llm")],
        ),
    )

    with pytest.raises(BlueprintError, match="requires_llm=True"):
        execute_blueprint(bp, registry, NeuroCoreConfig())
