neurocore.config.schema
=======================

.. py:module:: neurocore.config.schema

.. autoapi-nested-parse::

   Pydantic models for neurocore.yaml configuration.

   The config hierarchy mirrors the YAML structure:

       project:
         name: "my-agent"
         version: "0.1.0"
       paths:
         skills: "skills"
         blueprints: "blueprints"
         data: "data"
         logs: "logs"
       logging:
         level: "INFO"
         format: "console"
         file: null
       skills:
         neuroweave:
           llm_provider: "anthropic"
           ...

   Environment variable override uses ``NEUROCORE_`` prefix with double
   underscore for nesting: ``NEUROCORE_LOGGING__LEVEL=DEBUG``



Classes
-------

.. toctree::
   :hidden:

   /autoapi/neurocore/config/schema/LogLevel
   /autoapi/neurocore/config/schema/LogFormat
   /autoapi/neurocore/config/schema/ProjectConfig
   /autoapi/neurocore/config/schema/PathsConfig
   /autoapi/neurocore/config/schema/LoggingConfig
   /autoapi/neurocore/config/schema/NeuroCoreConfig

.. autoapisummary::

   neurocore.config.schema.LogLevel
   neurocore.config.schema.LogFormat
   neurocore.config.schema.ProjectConfig
   neurocore.config.schema.PathsConfig
   neurocore.config.schema.LoggingConfig
   neurocore.config.schema.NeuroCoreConfig


