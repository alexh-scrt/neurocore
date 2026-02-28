neurocore.runtime.blueprint.Blueprint
=====================================

.. py:class:: neurocore.runtime.blueprint.Blueprint(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`


   Complete blueprint model.

   Represents a parsed blueprint YAML file. Validated structurally
   on load; skill name validation happens separately via `validate()`.

   .. attribute:: name

      Human-readable flow name.

   .. attribute:: version

      Blueprint version string.

   .. attribute:: description

      Optional description.

   .. attribute:: components

      List of component definitions (skill references).

   .. attribute:: flow

      Flow definition (sequential, conditional, or graph).


   .. py:attribute:: name
      :type:  str


   .. py:attribute:: version
      :type:  str
      :value: '1.0'



   .. py:attribute:: description
      :type:  str | None
      :value: None



   .. py:attribute:: components
      :type:  list[BlueprintComponent]
      :value: None



   .. py:attribute:: flow
      :type:  FlowDefinition


   .. py:method:: validate_unique_names(v: list[BlueprintComponent]) -> list[BlueprintComponent]
      :classmethod:



   .. py:method:: validate_step_references() -> Blueprint

      Ensure all steps/nodes reference defined components.


