neurocore.config.loader
=======================

.. py:module:: neurocore.config.loader

.. autoapi-nested-parse::

   Configuration loader for NeuroCore.

   Loads configuration with the following priority (highest wins):
       1. Environment variables (``NEUROCORE_`` prefix, double underscore for nesting)
       2. .env file (project root)
       3. neurocore.yaml
       4. Built-in defaults

   Usage::

       from neurocore.config import load_config

       # Auto-detect project root (walks up from cwd)
       config = load_config()

       # Explicit project root
       config = load_config(project_root=Path("/path/to/project"))

       # Explicit config file
       config = load_config(config_path=Path("custom-config.yaml"))



Functions
---------

.. autoapisummary::

   neurocore.config.loader.find_project_root
   neurocore.config.loader.load_config


Module Contents
---------------

.. py:function:: find_project_root(start: pathlib.Path | None = None) -> pathlib.Path | None

   Walk up from `start` looking for neurocore.yaml.

   :param start: Directory to begin searching from. Defaults to cwd.

   :returns: The directory containing neurocore.yaml, or None if not found.


.. py:function:: load_config(project_root: pathlib.Path | None = None, config_path: pathlib.Path | None = None) -> neurocore.config.schema.NeuroCoreConfig

   Load NeuroCore configuration.

   Priority (highest wins):
       1. Environment variables (NEUROCORE_*)
       2. .env file
       3. neurocore.yaml
       4. Built-in defaults (in schema.py)

   :param project_root: Explicit project root directory.
                        If not provided, walks up from cwd looking for neurocore.yaml.
   :param config_path: Explicit path to a config YAML file.
                       If provided, project_root defaults to its parent directory.

   :returns: Fully resolved NeuroCoreConfig.

   :raises ConfigError: If config file is specified but invalid.


