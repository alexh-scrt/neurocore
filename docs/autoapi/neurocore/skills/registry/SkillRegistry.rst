neurocore.skills.registry.SkillRegistry
=======================================

.. py:class:: neurocore.skills.registry.SkillRegistry

   Registry of discovered skill classes.

   Skills are keyed by their `skill_meta.name`. The registry enforces
   uniqueness — registering a second skill with the same name raises
   SkillError unless `replace=True` is passed (used for entry point
   precedence over directory scan).

   .. attribute:: _skills

      Mapping from skill name to skill class.


   .. py:method:: register(skill_class: type[neurocore.skills.base.Skill], *, replace: bool = False) -> None

      Register a skill class.

      :param skill_class: A Skill subclass with a valid skill_meta.
      :param replace: If True, overwrites existing registration
                      (used for entry point precedence).

      :raises SkillError: If skill_class is not a valid Skill subclass,
          or if a skill with the same name is already registered
          and replace is False.



   .. py:method:: get(name: str) -> type[neurocore.skills.base.Skill] | None

      Get a registered skill class by name.

      :param name: The skill's registered name (from skill_meta.name).

      :returns: The Skill subclass, or None if not found.



   .. py:method:: get_or_raise(name: str) -> type[neurocore.skills.base.Skill]

      Get a registered skill class by name, or raise.

      :param name: The skill's registered name.

      :returns: The Skill subclass.

      :raises SkillError: If no skill is registered with this name.



   .. py:method:: list_skills() -> list[str]

      List all registered skill names, sorted alphabetically.

      :returns: Sorted list of skill names.



   .. py:method:: list_skill_metas() -> list[neurocore.skills.base.SkillMeta]

      List metadata for all registered skills.

      :returns: List of SkillMeta instances, sorted by name.



   .. py:method:: create(name: str, *, instance_name: str | None = None) -> neurocore.skills.base.Skill

      Create an instance of a registered skill.

      :param name: The skill's registered name.
      :param instance_name: Optional name for the instance
                            (defaults to skill_meta.name).

      :returns: A new Skill instance.

      :raises SkillError: If no skill is registered with this name.


