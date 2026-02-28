neurocore.runtime.executor
==========================

.. py:module:: neurocore.runtime.executor

.. autoapi-nested-parse::

   Blueprint executor — wires skills into FlowEngine and runs them.

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



Functions
---------

.. autoapisummary::

   neurocore.runtime.executor.merge_skill_config
   neurocore.runtime.executor.execute_blueprint
   neurocore.runtime.executor.load_and_run


Module Contents
---------------

.. py:function:: merge_skill_config(neurocore_config: neurocore.config.schema.NeuroCoreConfig, skill_name: str, blueprint_config: dict[str, Any]) -> dict[str, Any]

   Merge skill configuration from neurocore.yaml and blueprint.

   Priority (highest wins):
       1. Blueprint component config (overlay)
       2. neurocore.yaml skills.<name> (base)

   :param neurocore_config: The project's NeuroCoreConfig.
   :param skill_name: The skill's registered name (for neurocore.yaml lookup).
   :param blueprint_config: Config from the blueprint's component definition.

   :returns: Merged config dict.


.. py:function:: execute_blueprint(blueprint: neurocore.runtime.blueprint.Blueprint, registry: neurocore.skills.registry.SkillRegistry, neurocore_config: neurocore.config.schema.NeuroCoreConfig, *, initial_data: dict[str, Any] | None = None) -> flowengine.FlowContext

   Execute a blueprint using FlowEngine.

   This is the core execution function. It:
   1. Validates skill references
   2. Creates and initializes skill instances with merged config
   3. Builds a FlowEngine FlowConfig
   4. Executes via FlowEngine

   :param blueprint: Parsed Blueprint.
   :param registry: SkillRegistry with discovered skills.
   :param neurocore_config: Project configuration.
   :param initial_data: Optional initial context data (key-value pairs).

   :returns: FlowContext with execution results.

   :raises BlueprintError: If validation or instantiation fails.
   :raises ExecutionError: If execution fails.


.. py:function:: load_and_run(blueprint_path: pathlib.Path, *, project_root: pathlib.Path | None = None, initial_data: dict[str, Any] | None = None) -> flowengine.FlowContext

   High-level function: load config, discover skills, execute blueprint.

   Convenience wrapper that does everything:
   1. Load neurocore.yaml config
   2. Discover all skills (directory + entry points)
   3. Load and parse the blueprint
   4. Execute via FlowEngine

   :param blueprint_path: Path to the blueprint YAML file.
   :param project_root: Optional project root (auto-detected if not provided).
   :param initial_data: Optional initial context data.

   :returns: FlowContext with execution results.


