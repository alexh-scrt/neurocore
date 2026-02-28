neurocore.skills.registry
=========================

.. py:module:: neurocore.skills.registry

.. autoapi-nested-parse::

   Skill registry — holds discovered skill classes and creates instances.

   The SkillRegistry is the central index of all available skills. It is
   populated by the discovery mechanisms (directory scan + entry points)
   and used by the runtime to instantiate skills referenced in blueprints.

   Usage:
       from neurocore.skills.registry import SkillRegistry

       registry = SkillRegistry()
       registry.register(EchoSkill)
       skill_cls = registry.get("echo")
       all_skills = registry.list_skills()



Classes
-------

.. toctree::
   :hidden:

   /autoapi/neurocore/skills/registry/SkillRegistry

.. autoapisummary::

   neurocore.skills.registry.SkillRegistry


