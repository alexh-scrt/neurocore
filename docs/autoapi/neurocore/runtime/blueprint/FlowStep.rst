neurocore.runtime.blueprint.FlowStep
====================================

.. py:class:: neurocore.runtime.blueprint.FlowStep(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`


   A step in a sequential or conditional flow.


   .. py:attribute:: component
      :type:  str


   .. py:attribute:: description
      :type:  str | None
      :value: None



   .. py:attribute:: condition
      :type:  str | None
      :value: None



   .. py:attribute:: on_error
      :type:  Literal['fail', 'skip', 'continue']
      :value: 'fail'


