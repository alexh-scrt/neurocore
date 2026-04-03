"""T8: Blueprint parser & validator tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from neurocore.errors import BlueprintError
from neurocore.runtime.blueprint import (
    Blueprint,
    BlueprintComponent,
    FlowDefinition,
    FlowStep,
    load_blueprint,
    validate_blueprint,
)
from neurocore.skills.base import Skill, SkillMeta
from neurocore.skills.registry import SkillRegistry
from flowengine import FlowContext


# --- Helpers ---

VALID_BLUEPRINT_YAML = """\
name: "test-flow"
version: "1.0"
description: "A test flow"
components:
  - name: echo1
    type: echo
    config:
      message: "hello"
  - name: echo2
    type: echo
flow:
  type: sequential
  steps:
    - component: echo1
    - component: echo2
"""

GRAPH_BLUEPRINT_YAML = """\
name: "graph-flow"
components:
  - name: start
    type: echo
  - name: end
    type: echo
flow:
  type: graph
  nodes:
    - id: n1
      component: start
    - id: n2
      component: end
  edges:
    - source: n1
      target: n2
"""


class EchoSkill(Skill):
    skill_meta = SkillMeta(name="echo", version="0.1.0")

    def process(self, context: FlowContext) -> FlowContext:
        return context


class UpperSkill(Skill):
    skill_meta = SkillMeta(name="upper", version="0.1.0")

    def process(self, context: FlowContext) -> FlowContext:
        return context


@pytest.fixture
def registry() -> SkillRegistry:
    reg = SkillRegistry()
    reg.register(EchoSkill)
    reg.register(UpperSkill)
    return reg


# --- Blueprint model tests ---


class TestBlueprintModel:
    def test_minimal_blueprint(self):
        bp = Blueprint(
            name="test",
            components=[BlueprintComponent(name="a", type="echo")],
            flow=FlowDefinition(
                type="sequential",
                steps=[FlowStep(component="a")],
            ),
        )
        assert bp.name == "test"
        assert len(bp.components) == 1

    def test_defaults(self):
        bp = Blueprint(
            name="test",
            components=[BlueprintComponent(name="a", type="echo")],
            flow=FlowDefinition(steps=[FlowStep(component="a")]),
        )
        assert bp.version == "1.0"
        assert bp.description is None
        assert bp.flow.type == "sequential"

    def test_duplicate_component_names_rejected(self):
        with pytest.raises(ValueError, match="Duplicate component names"):
            Blueprint(
                name="test",
                components=[
                    BlueprintComponent(name="a", type="echo"),
                    BlueprintComponent(name="a", type="upper"),
                ],
                flow=FlowDefinition(steps=[FlowStep(component="a")]),
            )

    def test_step_references_undefined_component(self):
        with pytest.raises(ValueError, match="undefined component.*nonexistent"):
            Blueprint(
                name="test",
                components=[BlueprintComponent(name="a", type="echo")],
                flow=FlowDefinition(steps=[FlowStep(component="nonexistent")]),
            )

    def test_empty_components_rejected(self):
        with pytest.raises(ValueError):
            Blueprint(
                name="test",
                components=[],
                flow=FlowDefinition(steps=[FlowStep(component="a")]),
            )

    def test_sequential_requires_steps(self):
        with pytest.raises(ValueError, match="requires 'steps'"):
            Blueprint(
                name="test",
                components=[BlueprintComponent(name="a", type="echo")],
                flow=FlowDefinition(type="sequential"),
            )

    def test_graph_requires_nodes(self):
        with pytest.raises(ValueError, match="requires 'nodes'"):
            Blueprint(
                name="test",
                components=[BlueprintComponent(name="a", type="echo")],
                flow=FlowDefinition(type="graph"),
            )

    def test_graph_blueprint_valid(self):
        bp = Blueprint(
            name="test",
            components=[
                BlueprintComponent(name="a", type="echo"),
                BlueprintComponent(name="b", type="upper"),
            ],
            flow=FlowDefinition(
                type="graph",
                nodes=[
                    {"id": "n1", "component": "a"},
                    {"id": "n2", "component": "b"},
                ],
                edges=[{"source": "n1", "target": "n2"}],
            ),
        )
        assert len(bp.flow.nodes) == 2

    def test_graph_duplicate_node_ids_rejected(self):
        with pytest.raises(ValueError, match="Duplicate node IDs"):
            Blueprint(
                name="test",
                components=[BlueprintComponent(name="a", type="echo")],
                flow=FlowDefinition(
                    type="graph",
                    nodes=[
                        {"id": "n1", "component": "a"},
                        {"id": "n1", "component": "a"},
                    ],
                    edges=[{"source": "n1", "target": "n1"}],
                ),
            )

    def test_component_config_passthrough(self):
        bp = Blueprint(
            name="test",
            components=[
                BlueprintComponent(name="a", type="echo", config={"key": "val"}),
            ],
            flow=FlowDefinition(steps=[FlowStep(component="a")]),
        )
        assert bp.components[0].config == {"key": "val"}


# --- load_blueprint tests ---


class TestLoadBlueprint:
    def test_loads_valid_yaml(self, tmp_path: Path):
        bp_file = tmp_path / "flow.yaml"
        bp_file.write_text(VALID_BLUEPRINT_YAML)
        bp = load_blueprint(bp_file)
        assert bp.name == "test-flow"
        assert len(bp.components) == 2
        assert bp.components[0].config == {"message": "hello"}

    def test_loads_graph_blueprint(self, tmp_path: Path):
        bp_file = tmp_path / "graph.yaml"
        bp_file.write_text(GRAPH_BLUEPRINT_YAML)
        bp = load_blueprint(bp_file)
        assert bp.flow.type == "graph"
        assert len(bp.flow.nodes) == 2

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(BlueprintError, match="not found"):
            load_blueprint(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml(self, tmp_path: Path):
        bp_file = tmp_path / "bad.yaml"
        bp_file.write_text("{{{{invalid")
        with pytest.raises(BlueprintError, match="Invalid YAML"):
            load_blueprint(bp_file)

    def test_not_a_dict(self, tmp_path: Path):
        bp_file = tmp_path / "list.yaml"
        bp_file.write_text("- item1\n- item2")
        with pytest.raises(BlueprintError, match="YAML mapping"):
            load_blueprint(bp_file)

    def test_missing_required_fields(self, tmp_path: Path):
        bp_file = tmp_path / "incomplete.yaml"
        bp_file.write_text("name: test\n")
        with pytest.raises(BlueprintError, match="Invalid blueprint"):
            load_blueprint(bp_file)


# --- validate_blueprint tests ---


class TestValidateBlueprint:
    def test_valid_blueprint(self, registry: SkillRegistry):
        bp = Blueprint(
            name="test",
            components=[BlueprintComponent(name="a", type="echo")],
            flow=FlowDefinition(steps=[FlowStep(component="a")]),
        )
        errors = validate_blueprint(bp, registry)
        assert errors == []

    def test_unknown_skill(self, registry: SkillRegistry):
        bp = Blueprint(
            name="test",
            components=[BlueprintComponent(name="a", type="nonexistent")],
            flow=FlowDefinition(steps=[FlowStep(component="a")]),
        )
        errors = validate_blueprint(bp, registry)
        assert len(errors) == 1
        assert "nonexistent" in errors[0]

    def test_multiple_unknown_skills(self, registry: SkillRegistry):
        bp = Blueprint(
            name="test",
            components=[
                BlueprintComponent(name="a", type="missing1"),
                BlueprintComponent(name="b", type="missing2"),
            ],
            flow=FlowDefinition(
                steps=[FlowStep(component="a"), FlowStep(component="b")]
            ),
        )
        errors = validate_blueprint(bp, registry)
        assert len(errors) == 2

    def test_mix_of_valid_and_invalid(self, registry: SkillRegistry):
        bp = Blueprint(
            name="test",
            components=[
                BlueprintComponent(name="a", type="echo"),
                BlueprintComponent(name="b", type="unknown"),
            ],
            flow=FlowDefinition(
                steps=[FlowStep(component="a"), FlowStep(component="b")]
            ),
        )
        errors = validate_blueprint(bp, registry)
        assert len(errors) == 1
        assert "unknown" in errors[0]
