neurocore
=========

.. py:module:: neurocore

.. autoapi-nested-parse::

   NeuroCore: Pluggable, YAML-driven framework for building agentic AI applications.

   NeuroCore is the chassis for agentic AI — it wires together:
   - FlowEngine for workflow orchestration (DAG, sequential, conditional, cyclic)
   - Skills as discoverable, configurable components with metadata
   - YAML-based configuration with environment variable overlay
   - A CLI for scaffolding, running, and inspecting projects

   Example::

       from neurocore import Skill, SkillMeta

       class MySkill(Skill):
           skill_meta = SkillMeta(
               name="my-skill",
               version="0.1.0",
               description="A custom skill",
           )

           def process(self, context):
               context.set("result", "hello from my skill")
               return context



Submodules
----------

.. toctree::
   :maxdepth: 1

   /autoapi/neurocore/cli/index
   /autoapi/neurocore/config/index
   /autoapi/neurocore/errors/index
   /autoapi/neurocore/logging/index
   /autoapi/neurocore/runtime/index
   /autoapi/neurocore/scaffold/index
   /autoapi/neurocore/skills/index


