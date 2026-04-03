"""Blueprint parser and validator for NeuroCore.

A blueprint is a YAML file that defines a FlowEngine flow using
skill names (not Python class paths). The runtime resolves skill
names to classes via the SkillRegistry.

Blueprint format:

.. code-block:: yaml

    name: "my-flow"
    version: "1.0"
    description: "Optional description"
    components:
      - name: memory
        type: neuroweave          # Skill name from registry
        config:
          llm_model: "claude-haiku-4-5-20251001"
      - name: search
        type: web-search
        config:
          max_results: 10
    flow:
      type: sequential
      steps:
        - component: memory
        - component: search
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from neurocore.errors import BlueprintError
from neurocore.skills.registry import SkillRegistry


class BlueprintComponent(BaseModel):
    """A component definition in a blueprint.

    Unlike FlowEngine's ComponentConfig where `type` is a Python class path,
    here `type` is a skill name that gets resolved via the SkillRegistry.

    Attributes:
        name: Instance name (used in flow steps/nodes).
        type: Skill name from the SkillRegistry.
        config: Blueprint-level config overlay (merged with neurocore.yaml).
    """

    name: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class FlowStep(BaseModel):
    """A step in a sequential or conditional flow."""

    component: str
    description: str | None = None
    condition: str | None = None
    on_error: Literal["fail", "skip", "continue"] = "fail"


class FlowGraph(BaseModel):
    """Graph node definition."""

    id: str
    component: str
    description: str | None = None
    on_error: Literal["fail", "skip", "continue"] = "fail"


class FlowEdge(BaseModel):
    """Graph edge definition."""

    source: str
    target: str
    port: str | None = None


class FlowDefinition(BaseModel):
    """Flow structure definition."""

    type: Literal["sequential", "conditional", "graph"] = "sequential"
    settings: dict[str, Any] = Field(default_factory=dict)
    steps: list[FlowStep] | None = None
    nodes: list[FlowGraph] | None = None
    edges: list[FlowEdge] | None = None

    @model_validator(mode="after")
    def validate_flow_structure(self) -> FlowDefinition:
        if self.type in ("sequential", "conditional"):
            if not self.steps:
                raise ValueError(
                    f"'{self.type}' flow requires 'steps'"
                )
        elif self.type == "graph":
            if not self.nodes or not self.edges:
                raise ValueError(
                    "Graph flow requires 'nodes' and 'edges' to be defined."
                )
        return self


class Blueprint(BaseModel):
    """Complete blueprint model.

    Represents a parsed blueprint YAML file. Validated structurally
    on load; skill name validation happens separately via `validate()`.

    Attributes:
        name: Human-readable flow name.
        version: Blueprint version string.
        description: Optional description.
        components: List of component definitions (skill references).
        flow: Flow definition (sequential, conditional, or graph).
    """

    name: str
    version: str = "1.0"
    description: str | None = None
    components: list[BlueprintComponent] = Field(min_length=1)
    flow: FlowDefinition

    @field_validator("components")
    @classmethod
    def validate_unique_names(
        cls, v: list[BlueprintComponent]
    ) -> list[BlueprintComponent]:
        names = [c.name for c in v]
        if len(names) != len(set(names)):
            dupes = {n for n in names if names.count(n) > 1}
            raise ValueError(f"Duplicate component names: {dupes}")
        return v

    @model_validator(mode="after")
    def validate_step_references(self) -> Blueprint:
        """Ensure all steps/nodes reference defined components."""
        component_names = {c.name for c in self.components}

        if self.flow.steps:
            for step in self.flow.steps:
                if step.component not in component_names:
                    raise ValueError(
                        f"Step references undefined component: '{step.component}'"
                    )

        if self.flow.nodes:
            node_ids = [n.id for n in self.flow.nodes]
            if len(node_ids) != len(set(node_ids)):
                dupes = {nid for nid in node_ids if node_ids.count(nid) > 1}
                raise ValueError(f"Duplicate node IDs: {dupes}")

            for node in self.flow.nodes:
                if node.component not in component_names:
                    raise ValueError(
                        f"Node '{node.id}' references undefined component: "
                        f"'{node.component}'"
                    )

            if self.flow.edges:
                node_id_set = set(node_ids)
                for edge in self.flow.edges:
                    if edge.source not in node_id_set:
                        raise ValueError(
                            f"Edge source '{edge.source}' not in nodes"
                        )
                    if edge.target not in node_id_set:
                        raise ValueError(
                            f"Edge target '{edge.target}' not in nodes"
                        )

        return self


def load_blueprint(path: Path) -> Blueprint:
    """Load and parse a blueprint YAML file.

    Args:
        path: Path to the blueprint YAML file.

    Returns:
        Parsed Blueprint model.

    Raises:
        BlueprintError: If the file cannot be read, parsed, or validated.
    """
    path = Path(path)
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise BlueprintError(f"Blueprint file not found: {path}")
    except yaml.YAMLError as e:
        raise BlueprintError(f"Invalid YAML in blueprint {path}: {e}")

    if not isinstance(data, dict):
        raise BlueprintError(f"Blueprint must be a YAML mapping, got {type(data).__name__}")

    try:
        return Blueprint(**data)
    except Exception as e:
        raise BlueprintError(f"Invalid blueprint {path}: {e}")


def validate_blueprint(blueprint: Blueprint, registry: SkillRegistry) -> list[str]:
    """Validate that all skill references in a blueprint can be resolved.

    Checks that every `components[].type` matches a registered skill.

    Args:
        blueprint: Parsed blueprint.
        registry: SkillRegistry with discovered skills.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors: list[str] = []
    for comp in blueprint.components:
        if comp.type not in registry:
            available = ", ".join(registry.list_skills()) or "(none)"
            errors.append(
                f"Component '{comp.name}' references unknown skill '{comp.type}'. "
                f"Available: {available}"
            )
    return errors
