"""Tests for the SkillMeta -> FlowEngine ComponentMeta bridge (v0.5.0)."""

import pytest

from neurocore.skills import Skill, SkillMeta, skillmeta_to_componentmeta
from neurocore.skills.registry import SkillRegistry

# These tests require a FlowEngine that exposes the agent-native API (>=0.5.0).
pytest.importorskip("flowengine.agent.meta")


class EchoSkill(Skill):
    skill_meta = SkillMeta(
        name="echo",
        version="0.2.0",
        description="Echoes input to output.",
        provides=["echo_output"],
        consumes=["echo_input"],
        tags=["demo", "io"],
        config_schema={"type": "object", "properties": {"prefix": {"type": "string"}}},
        requires_llm=True,
    )

    def process(self, context):
        context.set("echo_output", context.get("echo_input", ""))
        return context


def test_skillmeta_maps_to_componentmeta():
    cmeta = skillmeta_to_componentmeta(EchoSkill.skill_meta)
    assert cmeta is not None
    assert cmeta.name == "echo"
    assert cmeta.version == "0.2.0"
    # provides -> outputs, consumes -> inputs
    assert cmeta.input_keys == ["echo_input"]
    assert cmeta.output_keys == ["echo_output"]
    assert cmeta.tags == ["demo", "io"]
    assert cmeta.requires_llm is True
    assert cmeta.config_schema["type"] == "object"


def test_skill_get_meta_returns_componentmeta():
    cmeta = EchoSkill().get_meta()
    assert cmeta is not None
    assert cmeta.name == "echo"
    # Skills default to low risk / agent-safe.
    assert cmeta.is_safe_for_agents is True


def test_registry_component_catalog():
    registry = SkillRegistry()
    registry.register(EchoSkill)
    catalog = registry.component_catalog()
    assert len(catalog) == 1
    entry = catalog[0]
    assert entry["type"] == "echo"
    assert entry["inputs"] == {"echo_input": {}}
    assert entry["outputs"] == {"echo_output": {}}
    assert entry["requires_llm"] is True
