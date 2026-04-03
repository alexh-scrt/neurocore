"""Integration tests for retry/backoff with real skill execution (NC-FIX-002)."""

import pytest
from flowengine import FlowContext

from neurocore import AsyncSkill, SkillMeta
from neurocore.config.schema import NeuroCoreConfig
from neurocore.runtime.blueprint import Blueprint, BlueprintComponent, FlowDefinition, FlowStep
from neurocore.runtime.executor import execute_blueprint
from neurocore.skills.registry import SkillRegistry


class FlakySkill(AsyncSkill):
    """Fails twice, then succeeds."""

    skill_meta = SkillMeta(
        name="flaky",
        version="0.1.0",
        provides=["flaky_output"],
        max_retries=3,
        retry_delay_base=0.01,
        retry_delay_max=0.05,
    )
    call_count = 0

    async def process(self, context: FlowContext) -> FlowContext:
        FlakySkill.call_count += 1
        if FlakySkill.call_count < 3:
            raise ValueError(f"flaky failure #{FlakySkill.call_count}")
        context.set("flaky_output", "recovered")
        return context


class PermanentlyFailingSkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="permanent-fail",
        version="0.1.0",
        max_retries=2,
        retry_delay_base=0.01,
        retry_delay_max=0.05,
    )

    async def process(self, context: FlowContext) -> FlowContext:
        raise ValueError("permanent failure")


class HealthySkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="healthy",
        version="0.1.0",
        provides=["healthy_output"],
        max_retries=3,
        retry_delay_base=0.01,
    )

    async def process(self, context: FlowContext) -> FlowContext:
        context.set("healthy_output", "fine")
        return context


def test_flaky_skill_succeeds_after_two_failures():
    FlakySkill.call_count = 0
    registry = SkillRegistry()
    registry.register(FlakySkill)

    bp = Blueprint(
        name="flaky-test",
        version="1.0",
        components=[BlueprintComponent(name="flaky", type="flaky")],
        flow=FlowDefinition(
            type="sequential",
            steps=[FlowStep(component="flaky")],
        ),
    )

    result = execute_blueprint(bp, registry, NeuroCoreConfig())
    assert result.get("flaky_output") == "recovered"
    assert FlakySkill.call_count == 3


def test_permanently_failing_skill_raises_after_max_retries():
    registry = SkillRegistry()
    registry.register(PermanentlyFailingSkill)

    bp = Blueprint(
        name="fail-test",
        version="1.0",
        components=[BlueprintComponent(name="fail", type="permanent-fail")],
        flow=FlowDefinition(
            type="sequential",
            steps=[FlowStep(component="fail")],
        ),
    )

    from neurocore.errors import ExecutionError

    with pytest.raises(ExecutionError, match="permanent failure"):
        execute_blueprint(bp, registry, NeuroCoreConfig())


def test_backoff_does_not_slow_down_healthy_skill():
    import time

    registry = SkillRegistry()
    registry.register(HealthySkill)

    bp = Blueprint(
        name="healthy-test",
        version="1.0",
        components=[BlueprintComponent(name="healthy", type="healthy")],
        flow=FlowDefinition(
            type="sequential",
            steps=[FlowStep(component="healthy")],
        ),
    )

    start = time.time()
    result = execute_blueprint(bp, registry, NeuroCoreConfig())
    elapsed = time.time() - start
    assert result.get("healthy_output") == "fine"
    assert elapsed < 1.0  # should be near-instant
