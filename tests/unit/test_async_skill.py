"""Tests for NC-001 — Async Skill Execution."""

import pytest
from flowengine import FlowContext

from neurocore import AsyncSkill, Skill, SkillMeta, is_async_skill
from neurocore.errors import ExecutionError
from neurocore.runtime.blueprint import Blueprint, BlueprintComponent, FlowDefinition, FlowStep
from neurocore.runtime.executor import execute_blueprint
from neurocore.skills.registry import SkillRegistry


class SyncEcho(Skill):
    skill_meta = SkillMeta(name="sync-echo", version="0.1.0", provides=["echo"])

    def process(self, context: FlowContext) -> FlowContext:
        context.set("echo", context.get("input", ""))
        return context


class AsyncUpper(AsyncSkill):
    skill_meta = SkillMeta(name="async-upper", version="0.1.0", provides=["upper"])

    async def process(self, context: FlowContext) -> FlowContext:
        context.set("upper", context.get("input", "").upper())
        return context


class AsyncFailing(AsyncSkill):
    skill_meta = SkillMeta(name="async-fail", version="0.1.0")

    async def process(self, context: FlowContext) -> FlowContext:
        raise ValueError("async boom")


class AsyncAppender(AsyncSkill):
    skill_meta = SkillMeta(name="async-appender", version="0.1.0", provides=["appended"])

    async def process(self, context: FlowContext) -> FlowContext:
        context.set("appended", context.get("upper", "") + "-appended")
        return context


async def test_async_skill_process_is_awaited():
    """AsyncSkill.process() returns a coroutine that can be awaited."""
    skill = AsyncUpper()
    skill.init({})
    ctx = FlowContext()
    ctx.set("input", "hello")
    result = await skill.process(ctx)
    assert result.get("upper") == "HELLO"


def test_sync_skill_still_works_unchanged():
    skill = SyncEcho()
    skill.init({})
    ctx = FlowContext()
    ctx.set("input", "world")
    result = skill.process(ctx)
    assert result.get("echo") == "world"


def test_is_async_skill_returns_true_for_async():
    skill = AsyncUpper()
    assert is_async_skill(skill) is True


def test_is_async_skill_returns_false_for_sync():
    skill = SyncEcho()
    assert is_async_skill(skill) is False


def test_mixed_blueprint_async_and_sync_skills_run_correctly():
    registry = SkillRegistry()
    registry.register(SyncEcho)
    registry.register(AsyncUpper)

    bp = Blueprint(
        name="mixed",
        version="1.0",
        components=[
            BlueprintComponent(name="echo", type="sync-echo"),
            BlueprintComponent(name="upper", type="async-upper"),
        ],
        flow=FlowDefinition(
            type="sequential",
            steps=[
                FlowStep(component="echo"),
                FlowStep(component="upper"),
            ],
        ),
    )

    from neurocore.config.schema import NeuroCoreConfig

    config = NeuroCoreConfig()
    result = execute_blueprint(bp, registry, config, initial_data={"input": "hello"})
    assert result.get("echo") == "hello"
    assert result.get("upper") == "HELLO"


def test_async_skill_exception_propagates_as_execution_error():
    registry = SkillRegistry()
    registry.register(AsyncFailing)

    bp = Blueprint(
        name="fail-bp",
        version="1.0",
        components=[BlueprintComponent(name="fail", type="async-fail")],
        flow=FlowDefinition(
            type="sequential",
            steps=[FlowStep(component="fail")],
        ),
    )

    from neurocore.config.schema import NeuroCoreConfig

    with pytest.raises(ExecutionError, match="async boom"):
        execute_blueprint(bp, registry, NeuroCoreConfig(), initial_data={})


def test_async_skill_context_data_passes_between_steps():
    registry = SkillRegistry()
    registry.register(AsyncUpper)
    registry.register(AsyncAppender)

    bp = Blueprint(
        name="chain",
        version="1.0",
        components=[
            BlueprintComponent(name="upper", type="async-upper"),
            BlueprintComponent(name="appender", type="async-appender"),
        ],
        flow=FlowDefinition(
            type="sequential",
            steps=[
                FlowStep(component="upper"),
                FlowStep(component="appender"),
            ],
        ),
    )

    from neurocore.config.schema import NeuroCoreConfig

    result = execute_blueprint(bp, registry, NeuroCoreConfig(), initial_data={"input": "hi"})
    assert result.get("upper") == "HI"
    assert result.get("appended") == "HI-appended"
