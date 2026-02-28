neurocore.skills.base
=====================

.. py:module:: neurocore.skills.base

.. autoapi-nested-parse::

   Skill base class and SkillMeta — the core abstraction of NeuroCore.

   A Skill is a FlowEngine BaseComponent enhanced with declarative metadata
   (SkillMeta). The metadata enables discovery, validation, documentation,
   configuration injection, and dependency tracking.

   Usage:
       from neurocore.skills import Skill, SkillMeta

       class EchoSkill(Skill):
           skill_meta = SkillMeta(
               name="echo",
               version="0.1.0",
               description="Echoes input to output",
               provides=["echo_output"],
               consumes=["echo_input"],
           )

           def process(self, context):
               value = context.get("echo_input", "")
               context.set("echo_output", value)
               return context



Classes
-------

.. toctree::
   :hidden:

   /autoapi/neurocore/skills/base/SkillMeta
   /autoapi/neurocore/skills/base/Skill

.. autoapisummary::

   neurocore.skills.base.SkillMeta
   neurocore.skills.base.Skill


