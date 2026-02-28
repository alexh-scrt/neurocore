"""Blueprint executor — wires skills into FlowEngine and runs them.

The executor is the bridge between NeuroCore's skill system and
FlowEngine's execution engine. It:

1. Resolves skill names from the blueprint to Skill classes via the registry
2. Merges config: neurocore.yaml skills.<name> (base) + blueprint config (overlay)
3. Creates and initializes Skill instances
4. Builds a FlowEngine FlowConfig and component dict
5. Executes via FlowEngine

Usage:
    from neurocore.runtime import execute_blueprint, load_and_run

    # Low-level
    result = execute_blueprint(blueprint, registry, config)

    # High-level (load + discover + execute)
    result = load_and_run(blueprint_path, project_root=Path("."))
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowengine import (
    ComponentConfig,
    FlowConfig,
    FlowContext,
    FlowDefinition,
    FlowEngine,
    FlowSettings,
    StepConfig,
)

from neurocore.config.loader import load_config
from neurocore.config.schema import NeuroCoreConfig
from neurocore.errors import BlueprintError, ExecutionError
from neurocore.runtime.blueprint import Blueprint, load_blueprint, validate_blueprint
from neurocore.skills.base import Skill
from neurocore.skills.loader import discover_skills
from neurocore.skills.registry import SkillRegistry


def merge_skill_config(
    neurocore_config: NeuroCoreConfig,
    skill_name: str,
    blueprint_config: dict[str, Any],
) -> dict[str, Any]:
    """Merge skill configuration from neurocore.yaml and blueprint.

    Priority (highest wins):
        1. Blueprint component config (overlay)
        2. neurocore.yaml skills.<name> (base)

    Args:
        neurocore_config: The project's NeuroCoreConfig.
        skill_name: The skill's registered name (for neurocore.yaml lookup).
        blueprint_config: Config from the blueprint's component definition.

    Returns:
        Merged config dict.
    """
    base = neurocore_config.get_skill_config(skill_name)
    merged = {**base, **blueprint_config}
    return merged


def _create_skill_instances(
    blueprint: Blueprint,
    registry: SkillRegistry,
    neurocore_config: NeuroCoreConfig,
) -> tuple[dict[str, Skill], dict[str, dict[str, Any]]]:
    """Create and initialize Skill instances for a blueprint.

    Args:
        blueprint: Parsed blueprint.
        registry: SkillRegistry with discovered skills.
        neurocore_config: Project config for config merging.

    Returns:
        Tuple of:
        - Dict mapping component instance names to initialized Skill instances.
        - Dict mapping component instance names to their merged configs.

    Raises:
        BlueprintError: If a skill cannot be found or instantiated.
    """
    instances: dict[str, Skill] = {}
    merged_configs: dict[str, dict[str, Any]] = {}

    for comp in blueprint.components:
        # Resolve skill class from registry
        skill_cls = registry.get(comp.type)
        if skill_cls is None:
            raise BlueprintError(
                f"Component '{comp.name}' references unknown skill '{comp.type}'"
            )

        # Create instance with the component's instance name
        try:
            instance = skill_cls(name=comp.name)
        except Exception as e:
            raise BlueprintError(
                f"Failed to instantiate skill '{comp.type}' as '{comp.name}': {e}"
            )

        # Merge config and initialize
        merged_config = merge_skill_config(neurocore_config, comp.type, comp.config)
        instance.init(merged_config)

        # Validate config
        config_errors = instance.validate_config()
        if config_errors:
            raise BlueprintError(
                f"Skill '{comp.name}' ({comp.type}) config validation failed: "
                + "; ".join(config_errors)
            )

        instances[comp.name] = instance
        merged_configs[comp.name] = merged_config

    return instances, merged_configs


def _build_flow_config(
    blueprint: Blueprint,
    merged_configs: dict[str, dict[str, Any]] | None = None,
) -> FlowConfig:
    """Convert a NeuroCore Blueprint into a FlowEngine FlowConfig.

    Maps NeuroCore's blueprint model to FlowEngine's config schema,
    using fully qualified class paths for component types.

    Args:
        blueprint: Parsed NeuroCore blueprint.
        merged_configs: Optional mapping of component names to their
                       merged configs (neurocore.yaml + blueprint overlay).
                       If provided, these are used instead of blueprint-only
                       configs so FlowEngine initializes skills correctly.

    Returns:
        FlowEngine FlowConfig.
    """
    # Build component configs — use the skill class path as the type
    # (FlowEngine needs a type path, but since we provide pre-built
    # components, it won't actually load from the path. We use a
    # placeholder path based on the skill type name.)
    fe_components = []
    for comp in blueprint.components:
        # Use merged config if available, otherwise fall back to blueprint config
        config = (
            merged_configs.get(comp.name, comp.config)
            if merged_configs
            else comp.config
        )
        fe_components.append(
            ComponentConfig(
                name=comp.name,
                type=f"neurocore.skills.{comp.type}",
                config=config,
            )
        )

    # Build flow definition
    fe_flow_kwargs: dict[str, Any] = {
        "type": blueprint.flow.type,
    }

    if blueprint.flow.settings:
        fe_flow_kwargs["settings"] = FlowSettings(**blueprint.flow.settings)

    if blueprint.flow.steps:
        fe_flow_kwargs["steps"] = [
            StepConfig(
                component=step.component,
                description=step.description,
                condition=step.condition,
                on_error=step.on_error,
            )
            for step in blueprint.flow.steps
        ]

    if blueprint.flow.nodes:
        from flowengine import GraphNodeConfig, GraphEdgeConfig

        fe_flow_kwargs["nodes"] = [
            GraphNodeConfig(
                id=node.id,
                component=node.component,
                description=node.description,
                on_error=node.on_error,
            )
            for node in blueprint.flow.nodes
        ]

        if blueprint.flow.edges:
            fe_flow_kwargs["edges"] = [
                GraphEdgeConfig(
                    source=edge.source,
                    target=edge.target,
                    port=edge.port,
                )
                for edge in blueprint.flow.edges
            ]

    fe_flow = FlowDefinition(**fe_flow_kwargs)

    return FlowConfig(
        name=blueprint.name,
        version=blueprint.version,
        description=blueprint.description,
        components=fe_components,
        flow=fe_flow,
    )


def execute_blueprint(
    blueprint: Blueprint,
    registry: SkillRegistry,
    neurocore_config: NeuroCoreConfig,
    *,
    initial_data: dict[str, Any] | None = None,
) -> FlowContext:
    """Execute a blueprint using FlowEngine.

    This is the core execution function. It:
    1. Validates skill references
    2. Creates and initializes skill instances with merged config
    3. Builds a FlowEngine FlowConfig
    4. Executes via FlowEngine

    Args:
        blueprint: Parsed Blueprint.
        registry: SkillRegistry with discovered skills.
        neurocore_config: Project configuration.
        initial_data: Optional initial context data (key-value pairs).

    Returns:
        FlowContext with execution results.

    Raises:
        BlueprintError: If validation or instantiation fails.
        ExecutionError: If execution fails.
    """
    # Validate all skill references
    errors = validate_blueprint(blueprint, registry)
    if errors:
        raise BlueprintError(
            "Blueprint validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    # Create and initialize skill instances
    skill_instances, merged_configs = _create_skill_instances(
        blueprint, registry, neurocore_config
    )

    # Build FlowEngine config (with merged configs so FlowEngine
    # re-initializes components with the correct merged config)
    flow_config = _build_flow_config(blueprint, merged_configs)

    # Create FlowEngine with pre-built components (skip type validation)
    try:
        engine = FlowEngine(
            flow_config,
            skill_instances,
            validate_types=False,
        )
    except Exception as e:
        raise ExecutionError(f"Failed to create FlowEngine: {e}")

    # Build initial context
    context = FlowContext()
    if initial_data:
        for key, value in initial_data.items():
            context.set(key, value)

    # Execute
    try:
        result = engine.execute(context)
    except Exception as e:
        raise ExecutionError(f"Blueprint execution failed: {e}")

    return result


def load_and_run(
    blueprint_path: Path,
    *,
    project_root: Path | None = None,
    initial_data: dict[str, Any] | None = None,
) -> FlowContext:
    """High-level function: load config, discover skills, execute blueprint.

    Convenience wrapper that does everything:
    1. Load neurocore.yaml config
    2. Discover all skills (directory + entry points)
    3. Load and parse the blueprint
    4. Execute via FlowEngine

    Args:
        blueprint_path: Path to the blueprint YAML file.
        project_root: Optional project root (auto-detected if not provided).
        initial_data: Optional initial context data.

    Returns:
        FlowContext with execution results.
    """
    # Load config
    neurocore_config = load_config(project_root=project_root)

    # Discover skills
    registry = discover_skills(neurocore_config)

    # Load blueprint
    blueprint = load_blueprint(blueprint_path)

    # Execute
    return execute_blueprint(
        blueprint,
        registry,
        neurocore_config,
        initial_data=initial_data,
    )
