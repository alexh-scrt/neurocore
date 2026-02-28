neurocore.runtime.blueprint
===========================

.. py:module:: neurocore.runtime.blueprint

.. autoapi-nested-parse::

   Blueprint parser and validator for NeuroCore.

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



Classes
-------

.. toctree::
   :hidden:

   /autoapi/neurocore/runtime/blueprint/BlueprintComponent
   /autoapi/neurocore/runtime/blueprint/FlowStep
   /autoapi/neurocore/runtime/blueprint/FlowGraph
   /autoapi/neurocore/runtime/blueprint/FlowEdge
   /autoapi/neurocore/runtime/blueprint/FlowDefinition
   /autoapi/neurocore/runtime/blueprint/Blueprint

.. autoapisummary::

   neurocore.runtime.blueprint.BlueprintComponent
   neurocore.runtime.blueprint.FlowStep
   neurocore.runtime.blueprint.FlowGraph
   neurocore.runtime.blueprint.FlowEdge
   neurocore.runtime.blueprint.FlowDefinition
   neurocore.runtime.blueprint.Blueprint


Functions
---------

.. autoapisummary::

   neurocore.runtime.blueprint.load_blueprint
   neurocore.runtime.blueprint.validate_blueprint


Module Contents
---------------

.. py:function:: load_blueprint(path: pathlib.Path) -> Blueprint

   Load and parse a blueprint YAML file.

   :param path: Path to the blueprint YAML file.

   :returns: Parsed Blueprint model.

   :raises BlueprintError: If the file cannot be read, parsed, or validated.


.. py:function:: validate_blueprint(blueprint: Blueprint, registry: neurocore.skills.registry.SkillRegistry) -> list[str]

   Validate that all skill references in a blueprint can be resolved.

   Checks that every `components[].type` matches a registered skill.

   :param blueprint: Parsed blueprint.
   :param registry: SkillRegistry with discovered skills.

   :returns: List of validation error messages (empty if valid).


