neurocore.runtime.blueprint.BlueprintComponent
==============================================

.. py:class:: neurocore.runtime.blueprint.BlueprintComponent(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`


   A component definition in a blueprint.

   Unlike FlowEngine's ComponentConfig where `type` is a Python class path,
   here `type` is a skill name that gets resolved via the SkillRegistry.

   .. attribute:: name

      Instance name (used in flow steps/nodes).

   .. attribute:: type

      Skill name from the SkillRegistry.

   .. attribute:: config

      Blueprint-level config overlay (merged with neurocore.yaml).


   .. py:attribute:: name
      :type:  str


   .. py:attribute:: type
      :type:  str


   .. py:attribute:: config
      :type:  dict[str, Any]
      :value: None


