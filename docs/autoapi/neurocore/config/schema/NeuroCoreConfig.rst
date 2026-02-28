neurocore.config.schema.NeuroCoreConfig
=======================================

.. py:class:: neurocore.config.schema.NeuroCoreConfig(/, **data: Any)

   Bases: :py:obj:`pydantic.BaseModel`


   Top-level NeuroCore configuration model.

   Represents the full contents of neurocore.yaml plus any
   overrides from .env and environment variables.

   .. attribute:: project

      Project metadata (name, version).

   .. attribute:: paths

      Directory paths for skills, blueprints, data, logs.

   .. attribute:: logging

      Logging level, format, optional file output.

   .. attribute:: skills

      Per-skill configuration dicts, keyed by skill name.

   .. attribute:: project_root

      Resolved absolute path to the project root
      (the directory containing neurocore.yaml).
      Set by the ConfigLoader, not from YAML.


   .. py:attribute:: project
      :type:  ProjectConfig
      :value: None



   .. py:attribute:: paths
      :type:  PathsConfig
      :value: None



   .. py:attribute:: logging
      :type:  LoggingConfig
      :value: None



   .. py:attribute:: skills
      :type:  dict[str, dict[str, Any]]
      :value: None



   .. py:attribute:: project_root
      :type:  pathlib.Path
      :value: None



   .. py:method:: resolve_path(relative_path: str) -> pathlib.Path

      Resolve a path relative to project_root.

      Absolute paths are returned as-is. Relative paths are resolved
      against self.project_root.

      :param relative_path: A path string from the config.

      :returns: Resolved absolute Path.



   .. py:property:: skills_dir
      :type: pathlib.Path


      Resolved absolute path to the skills directory.


   .. py:property:: blueprints_dir
      :type: pathlib.Path


      Resolved absolute path to the blueprints directory.


   .. py:property:: data_dir
      :type: pathlib.Path


      Resolved absolute path to the data directory.


   .. py:property:: logs_dir
      :type: pathlib.Path


      Resolved absolute path to the logs directory.


   .. py:method:: get_skill_config(skill_name: str) -> dict[str, Any]

      Get configuration for a specific skill.

      :param skill_name: The skill's registered name.

      :returns: Config dict for the skill, or empty dict if not configured.


