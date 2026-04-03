"""Tests for NC-003 — Streaming Execution."""

import pytest
from flowengine import FlowContext

from neurocore import AsyncSkill, Skill, SkillMeta
from neurocore.config.schema import NeuroCoreConfig
from neurocore.runtime.blueprint import Blueprint, BlueprintComponent, FlowDefinition, FlowStep
from neurocore.runtime.events import FlowEventType
from neurocore.runtime.executor import execute_blueprint_stream
from neurocore.skills.registry import SkillRegistry


class EchoSkill(Skill):
    skill_meta = SkillMeta(name="echo", version="0.1.0", provides=["echo"])

    def process(self, context: FlowContext) -> FlowContext:
        context.set("echo", context.get("input", ""))
        return context


class FailSkill(AsyncSkill):
    skill_meta = SkillMeta(name="fail", version="0.1.0")

    async def process(self, context: FlowContext) -> FlowContext:
        raise RuntimeError("step failed")


def _make_bp(*components_and_steps):
    comps = [BlueprintComponent(name=c[0], type=c[1]) for c in components_and_steps]
    steps = [FlowStep(component=c[0]) for c in components_and_steps]
    return Blueprint(
        name="test-bp",
        version="1.0",
        components=comps,
        flow=FlowDefinition(type="sequential", steps=steps),
    )


def _make_registry(*skills):
    reg = SkillRegistry()
    for s in skills:
        reg.register(s)
    return reg


async def _collect_events(bp, registry, config, initial_data=None):
    events = []
    async for event in execute_blueprint_stream(bp, registry, config, initial_data):
        events.append(event)
    return events


async def test_stream_yields_flow_started_first():
    registry = _make_registry(EchoSkill)
    bp = _make_bp(("echo", "echo"))
    events = await _collect_events(bp, registry, NeuroCoreConfig())
    assert events[0].event_type == FlowEventType.FLOW_STARTED


async def test_stream_yields_step_started_for_each_skill():
    registry = _make_registry(EchoSkill)
    bp = _make_bp(("echo", "echo"))
    events = await _collect_events(bp, registry, NeuroCoreConfig())
    step_started = [e for e in events if e.event_type == FlowEventType.STEP_STARTED]
    assert len(step_started) == 1
    assert step_started[0].step_name == "echo"


async def test_stream_yields_step_completed_with_duration():
    registry = _make_registry(EchoSkill)
    bp = _make_bp(("echo", "echo"))
    events = await _collect_events(bp, registry, NeuroCoreConfig())
    completed = [e for e in events if e.event_type == FlowEventType.STEP_COMPLETED]
    assert len(completed) == 1
    assert completed[0].duration_ms is not None
    assert completed[0].duration_ms >= 0


async def test_stream_yields_flow_completed_last():
    registry = _make_registry(EchoSkill)
    bp = _make_bp(("echo", "echo"))
    events = await _collect_events(bp, registry, NeuroCoreConfig())
    assert events[-1].event_type == FlowEventType.FLOW_COMPLETED
    assert events[-1].duration_ms is not None


async def test_stream_step_failed_yields_step_failed_then_flow_failed():
    registry = _make_registry(FailSkill)
    bp = _make_bp(("fail", "fail"))
    events = []
    try:
        async for event in execute_blueprint_stream(bp, registry, NeuroCoreConfig()):
            events.append(event)
    except RuntimeError:
        pass
    types = [e.event_type for e in events]
    assert FlowEventType.STEP_FAILED in types
    assert FlowEventType.FLOW_FAILED in types


async def test_stream_step_failed_reraises_exception():
    registry = _make_registry(FailSkill)
    bp = _make_bp(("fail", "fail"))
    with pytest.raises(RuntimeError, match="step failed"):
        await _collect_events(bp, registry, NeuroCoreConfig())


async def test_stream_data_produced_contains_only_provided_keys():
    registry = _make_registry(EchoSkill)
    bp = _make_bp(("echo", "echo"))
    events = await _collect_events(bp, registry, NeuroCoreConfig(), initial_data={"input": "hi"})
    completed = [e for e in events if e.event_type == FlowEventType.STEP_COMPLETED]
    assert len(completed) == 1
    assert "echo" in completed[0].data
    assert "input" not in completed[0].data


def test_stream_is_async_generator():
    """execute_blueprint_stream should return an async iterator."""
    registry = _make_registry(EchoSkill)
    bp = _make_bp(("echo", "echo"))
    result = execute_blueprint_stream(bp, registry, NeuroCoreConfig())
    assert hasattr(result, "__aiter__")
    assert hasattr(result, "__anext__")


async def test_stream_timestamps_monotonically_increasing():
    registry = _make_registry(EchoSkill)
    bp = _make_bp(("echo", "echo"))
    events = await _collect_events(bp, registry, NeuroCoreConfig())
    timestamps = [e.timestamp for e in events]
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i - 1]
