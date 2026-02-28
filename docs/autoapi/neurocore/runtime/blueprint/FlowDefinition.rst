neurocore.runtime.blueprint.FlowDefinition
==========================================

.. py:class:: neurocore.runtime.blueprint.FlowDefinition(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`


   Flow structure definition.


   .. py:attribute:: type
      :type:  Literal['sequential', 'conditional', 'graph']
      :value: 'sequential'



   .. py:attribute:: settings
      :type:  dict[str, Any]
      :value: None



   .. py:attribute:: steps
      :type:  list[FlowStep] | None
      :value: None



   .. py:attribute:: nodes
      :type:  list[FlowGraph] | None
      :value: None



   .. py:attribute:: edges
      :type:  list[FlowEdge] | None
      :value: None



   .. py:method:: validate_flow_structure() -> FlowDefinition

