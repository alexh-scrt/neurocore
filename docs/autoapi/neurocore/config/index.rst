neurocore.config
================

.. py:module:: neurocore.config

.. autoapi-nested-parse::

   NeuroCore configuration system.

   Handles YAML config loading, .env overlay, environment variable
   overrides, and path resolution.

   Usage:
       from neurocore.config import load_config, NeuroCoreConfig

       config = load_config()  # auto-detects neurocore.yaml
       print(config.project.name)
       print(config.skills_dir)



Submodules
----------

.. toctree::
   :maxdepth: 1

   /autoapi/neurocore/config/defaults/index
   /autoapi/neurocore/config/loader/index
   /autoapi/neurocore/config/schema/index


