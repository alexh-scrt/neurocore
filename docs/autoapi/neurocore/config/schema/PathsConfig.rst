neurocore.config.schema.PathsConfig
===================================

.. py:class:: neurocore.config.schema.PathsConfig(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`


   Directory paths (relative to project root or absolute).

   Relative paths are resolved against `project_root` at load time
   by the ConfigLoader.


   .. py:attribute:: skills
      :type:  str
      :value: 'skills'



   .. py:attribute:: blueprints
      :type:  str
      :value: 'blueprints'



   .. py:attribute:: data
      :type:  str
      :value: 'data'



   .. py:attribute:: logs
      :type:  str
      :value: 'logs'


