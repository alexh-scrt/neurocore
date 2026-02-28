neurocore.runtime.blueprint.FlowGraph
=====================================

.. py:class:: neurocore.runtime.blueprint.FlowGraph(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`


   Graph node definition.


   .. py:attribute:: id
      :type:  str


   .. py:attribute:: component
      :type:  str


   .. py:attribute:: description
      :type:  str | None
      :value: None



   .. py:attribute:: on_error
      :type:  Literal['fail', 'skip', 'continue']
      :value: 'fail'


