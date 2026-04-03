"""Blueprint executor — wires skills into FlowEngine and runs them.

The executor is the bridge between NeuroCore's skill system and
FlowEngine's execution engine. It:

1. Resolves skill names from the blueprint to Skill classes via the registry
2. Merges config: neurocore.yaml skills.<name> (base) + blueprint config (overlay)
3. Creates and initializes Skill instances
4. Builds a FlowEngine FlowConfig and component dict
5. Executes via FlowEngine (sync or async)

Usage:
    from neurocore.runtime import execute_blueprint, load_and_run

    # Low-level
    result = execute_blueprint(blueprint, registry, config)

    # High-level (load + discover + execute)
    result = load_and_run(blueprint_path, project_root=Path("."))

    # Streaming
    async for event in execute_blueprint_stream(bp, registry, cfg):
        print(event.event_type, event.step_name)
"""

from __future__ import annotations

import asyncio
import random
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
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
from neurocore.logging import get_logger
from neurocore.runtime.blueprint import Blueprint, load_blueprint, validate_blueprint
from neurocore.skills.base import Skill, is_async_skill
from neurocore.skills.loader import discover_skills
from neurocore.skills.registry import SkillRegistry

log = get_logger("executor")


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
            ) from e

        # Merge config and initialize
        merged_config = merge_skill_config(neurocore_config, comp.type, comp.config)
        instance.init(merged_config)

        # Inject LLM provider if required
        if instance.skill_meta.requires_llm:
            from neurocore.llm.provider import build_provider

            instance.llm = build_provider(merged_config)
            if instance.llm is None:
                raise BlueprintError(
                    f"Skill '{comp.name}' has requires_llm=True but no llm_provider "
                    f"is configured. Set llm_provider in neurocore.yaml or blueprint config."
                )

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
        from flowengine import GraphEdgeConfig, GraphNodeConfig

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


# ---------------------------------------------------------------------------
# Async helpers
# ---------------------------------------------------------------------------

async def _run_skill_async(skill: Skill, context: FlowContext) -> FlowContext:
    """Execute a skill's process(), with automatic retry and exponential backoff.

    Retry behaviour is controlled by skill.skill_meta:
        max_retries=0        → no retry (default, backward-compatible)
        max_retries=3        → up to 3 retries after the first failure
        retry_on=()          → retry on any Exception when max_retries > 0
        retry_on=(SomeError,) → retry only those exceptions
        retry_delay_base=1.0 → first retry after ~1s
        retry_delay_max=60.0 → subsequent retries never wait longer than 60s
    """
    meta = skill.skill_meta
    max_retries: int = meta.max_retries
    retry_on: tuple[type[BaseException], ...] = meta.retry_on or (Exception,)
    base: float = meta.retry_delay_base
    max_delay: float = meta.retry_delay_max

    last_exc: BaseException | None = None

    for attempt in range(max_retries + 1):
        try:
            if is_async_skill(skill):
                return await skill.process(context)  # type: ignore[misc]
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, skill.process, context)

        except BaseException as exc:
            if max_retries == 0:
                raise

            if not isinstance(exc, retry_on):
                raise

            last_exc = exc

            if attempt == max_retries:
                break

            raw_delay = base * (2 ** attempt)
            capped_delay = min(raw_delay, max_delay)
            jittered_delay = random.uniform(0, capped_delay)

            log.warning(
                "skill.retry",
                skill=skill.name,
                attempt=attempt + 1,
                max_retries=max_retries,
                delay_seconds=round(jittered_delay, 2),
                exception_type=type(exc).__name__,
                exception_msg=str(exc)[:200],
            )
            await asyncio.sleep(jittered_delay)

    assert last_exc is not None  # noqa: S101
    raise last_exc


def _get_sequential_steps(blueprint: Blueprint) -> list[Any]:
    """Return the ordered list of flow steps for sequential/conditional flows."""
    if blueprint.flow.steps:
        return list(blueprint.flow.steps)
    return []


async def _execute_blueprint_async(
    blueprint: Blueprint,
    instances: dict[str, Skill],
    merged_configs: dict[str, dict[str, Any]],
    initial_data: dict[str, Any] | None,
) -> FlowContext:
    """Execute a sequential/conditional blueprint asynchronously."""
    context = FlowContext()
    if initial_data:
        for k, v in initial_data.items():
            context.set(k, v)
    steps = _get_sequential_steps(blueprint)
    for step in steps:
        skill = instances[step.component]
        context = await _run_skill_async(skill, context)
    return context


async def _execute_dag_concurrent(
    blueprint: Blueprint,
    instances: dict[str, Skill],
    merged_configs: dict[str, dict[str, Any]],
    initial_data: dict[str, Any] | None,
) -> FlowContext:
    """Execute a DAG blueprint with concurrent layers."""
    edges = blueprint.flow.edges or []
    nodes = blueprint.flow.nodes or []
    in_degree: dict[str, int] = {n.id: 0 for n in nodes}
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adjacency[edge.source].append(edge.target)
        in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

    # Kahn's algorithm to get layers
    queue: deque[str] = deque(k for k, v in in_degree.items() if v == 0)
    layers: list[list[str]] = []
    visited = 0
    while queue:
        layer = list(queue)
        layers.append(layer)
        visited += len(layer)
        queue.clear()
        for node_id in layer:
            for neighbour in adjacency[node_id]:
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)

    if visited != len(nodes):
        raise BlueprintError("DAG contains a cycle — topological sort failed.")

    # Map node IDs to component names
    node_to_component = {n.id: n.component for n in nodes}

    # Execute each layer concurrently
    context = FlowContext()
    if initial_data:
        for k, v in initial_data.items():
            context.set(k, v)
    for layer in layers:
        layer_skills = [instances[node_to_component[node_id]] for node_id in layer]
        results = await asyncio.gather(
            *[_run_skill_async(skill, context) for skill in layer_skills]
        )
        # Merge results into context (last write wins per key)
        for result_ctx in results:
            for key, value in result_ctx.data.items():
                context.set(key, value)

    return context


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute_blueprint(
    blueprint: Blueprint,
    registry: SkillRegistry,
    neurocore_config: NeuroCoreConfig,
    *,
    initial_data: dict[str, Any] | None = None,
) -> FlowContext:
    """Execute a blueprint. Supports both sync and async skills.

    This is the core execution function. It:
    1. Validates skill references
    2. Creates and initializes skill instances with merged config
    3. Detects async skills and chooses execution path
    4. For sync-only blueprints, delegates to FlowEngine
    5. For async blueprints, uses asyncio event loop

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

    has_async = any(is_async_skill(s) for s in skill_instances.values())

    if has_async or blueprint.flow.type == "graph":
        # Async path: handles async skills and DAG concurrent execution
        try:
            if blueprint.flow.type == "graph" and blueprint.flow.edges:
                return asyncio.run(
                    _execute_dag_concurrent(
                        blueprint, skill_instances, merged_configs, initial_data
                    )
                )
            return asyncio.run(
                _execute_blueprint_async(
                    blueprint, skill_instances, merged_configs, initial_data
                )
            )
        except Exception as e:
            if isinstance(e, (BlueprintError, ExecutionError)):
                raise
            raise ExecutionError(f"Blueprint execution failed: {e}") from e

    # Sync path: use FlowEngine for backward compatibility
    flow_config = _build_flow_config(blueprint, merged_configs)
    try:
        engine = FlowEngine(
            flow_config,
            skill_instances,
            validate_types=False,
        )
    except Exception as e:
        raise ExecutionError(f"Failed to create FlowEngine: {e}") from e

    context = FlowContext()
    if initial_data:
        for key, value in initial_data.items():
            context.set(key, value)

    try:
        result = engine.execute(context)
    except Exception as e:
        raise ExecutionError(f"Blueprint execution failed: {e}") from e

    return result


async def execute_blueprint_stream(
    blueprint: Blueprint,
    registry: SkillRegistry,
    config: NeuroCoreConfig,
    initial_data: dict[str, Any] | None = None,
) -> AsyncIterator[Any]:
    """Execute a blueprint, yielding FlowEvents as each step runs.

    Usage:
        async for event in execute_blueprint_stream(bp, registry, cfg):
            print(event.event_type, event.step_name)
    """
    from neurocore.runtime.events import FlowEvent, FlowEventType

    instances, merged_configs = _create_skill_instances(blueprint, registry, config)
    steps = _get_sequential_steps(blueprint)

    flow_start = time.time()
    yield FlowEvent(FlowEventType.FLOW_STARTED, step_name="", data={"blueprint": blueprint.name})

    context = FlowContext()
    if initial_data:
        for k, v in initial_data.items():
            context.set(k, v)
    for step in steps:
        skill = instances[step.component]
        step_start = time.time()
        yield FlowEvent(FlowEventType.STEP_STARTED, step_name=step.component)
        try:
            context = await _run_skill_async(skill, context)
            duration = (time.time() - step_start) * 1000
            yield FlowEvent(
                FlowEventType.STEP_COMPLETED,
                step_name=step.component,
                duration_ms=duration,
                data={k: v for k, v in context.data.items()
                      if k in (skill.skill_meta.provides or [])},
            )
        except Exception as exc:
            duration = (time.time() - step_start) * 1000
            yield FlowEvent(
                FlowEventType.STEP_FAILED,
                step_name=step.component,
                duration_ms=duration,
                error=str(exc),
            )
            yield FlowEvent(
                FlowEventType.FLOW_FAILED,
                step_name="",
                duration_ms=(time.time() - flow_start) * 1000,
                error=str(exc),
            )
            raise

    yield FlowEvent(
        FlowEventType.FLOW_COMPLETED,
        step_name="",
        duration_ms=(time.time() - flow_start) * 1000,
    )


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
