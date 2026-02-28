neurocore.skills.base.Skill
===========================

.. py:class:: neurocore.skills.base.Skill(name: str | None = None)

   Bases: :py:obj:`flowengine.BaseComponent`


   Base class for all NeuroCore skills.

   Extends FlowEngine's BaseComponent with:
   - Declarative metadata via `skill_meta` (SkillMeta)
   - Config validation against JSON Schema
   - Health check with initialization guard

   Subclasses MUST:
   1. Define `skill_meta` as a class attribute (SkillMeta instance)
   2. Implement `process(context) -> context`

   Subclasses MAY override:
   - `init(config)` — for one-time setup (call super().init(config))
   - `setup(context)` — per-run preparation
   - `teardown(context)` — per-run cleanup
   - `validate_config()` — additional validation beyond schema
   - `health_check()` — custom health checking

   Lifecycle:
       1. __init__(name)       — instance creation (name defaults to skill_meta.name)
       2. init(config)         — configuration (once)
       3. setup(context)       — pre-processing (each run)
       4. process(context)     — main logic (each run)
       5. teardown(context)    — cleanup (each run)

   Example::

       class GreetSkill(Skill):
           skill_meta = SkillMeta(
               name="greet",
               version="1.0.0",
               description="Greets the user by name",
               provides=["greeting"],
               consumes=["user_name"],
           )

           def process(self, context: FlowContext) -> FlowContext:
               name = context.get("user_name", "World")
               context.set("greeting", f"Hello, {name}!")
               return context


   .. py:attribute:: skill_meta
      :type:  ClassVar[SkillMeta]


   .. py:method:: validate_config() -> list[str]

      Validate component configuration.

      Checks required keys from config_schema if provided.
      Subclasses can override to add custom validation.

      :returns: List of validation error messages (empty if valid).



   .. py:method:: health_check() -> bool

      Check if skill is healthy.

      Returns True if the skill has been initialized.
      Subclasses can override for custom health checks
      (e.g., checking external service connectivity).

      :returns: True if skill is operational.


