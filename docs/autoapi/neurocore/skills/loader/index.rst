neurocore.skills.loader
=======================

.. py:module:: neurocore.skills.loader

.. autoapi-nested-parse::

   Skill discovery — directory scan + entry points.

   Two discovery mechanisms, merged into a unified SkillRegistry:

   1. **Directory scan** — walks a skills/ directory, imports .py files,
      finds Skill subclasses.
   2. **Entry points** — scans the `neurocore.skills` group from installed
      packages (pyproject.toml [project.entry-points."neurocore.skills"]).

   Entry points take precedence — a pip-installed skill wins over a
   local copy with the same name.

   Usage:
       from neurocore.skills.loader import discover_skills
       from neurocore.config import load_config

       config = load_config()
       registry = discover_skills(config)
       print(registry.list_skills())



Attributes
----------

.. autoapisummary::

   neurocore.skills.loader.ENTRY_POINT_GROUP


Functions
---------

.. autoapisummary::

   neurocore.skills.loader.discover_directory
   neurocore.skills.loader.discover_entry_points
   neurocore.skills.loader.discover_skills


Module Contents
---------------

.. py:data:: ENTRY_POINT_GROUP
   :value: 'neurocore.skills'


.. py:function:: discover_directory(skills_dir: pathlib.Path, *, registry: neurocore.skills.registry.SkillRegistry | None = None) -> neurocore.skills.registry.SkillRegistry

   Discover skills by scanning a directory for .py files.

   Walks the directory (non-recursive by default), imports each .py
   file as a module, and finds all Skill subclasses with valid
   skill_meta.

   :param skills_dir: Path to the skills directory.
   :param registry: Existing registry to add to. Creates a new one if None.

   :returns: SkillRegistry with discovered skills.

   :raises SkillError: If a skill file cannot be imported (logged, not fatal).


.. py:function:: discover_entry_points(*, registry: neurocore.skills.registry.SkillRegistry | None = None) -> neurocore.skills.registry.SkillRegistry

   Discover skills from installed package entry points.

   Scans the `neurocore.skills` entry point group. Each entry point
   should point to a Skill subclass.

   Entry point format in pyproject.toml:
       [project.entry-points."neurocore.skills"]
       neuroweave = "neurocore_skill_neuroweave:NeuroWeaveSkill"

   :param registry: Existing registry to add to. Creates a new one if None.

   :returns: SkillRegistry with discovered skills.


.. py:function:: discover_skills(config: neurocore.config.schema.NeuroCoreConfig, *, registry: neurocore.skills.registry.SkillRegistry | None = None) -> neurocore.skills.registry.SkillRegistry

   Discover all skills — directory scan + entry points.

   Discovery order:
   1. Directory scan (skills/ folder) — baseline
   2. Entry points (pip-installed packages) — override duplicates

   This means entry-point skills take precedence over local skills
   with the same name.

   :param config: NeuroCoreConfig with skills_dir path.
   :param registry: Existing registry to add to. Creates a new one if None.

   :returns: SkillRegistry with all discovered skills.


