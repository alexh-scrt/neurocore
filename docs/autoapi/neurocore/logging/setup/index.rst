neurocore.logging.setup
=======================

.. py:module:: neurocore.logging.setup

.. autoapi-nested-parse::

   NeuroCore structured logging — configures structlog for the entire application.

   Reuses the same pattern as NeuroWeave: structlog with console (colored, dev)
   and JSON (machine-parseable, production) modes. Adds optional file handler
   support for persistent log output.

   Usage:
       from neurocore.logging import configure_logging, get_logger
       from neurocore.config import load_config

       config = load_config()
       configure_logging(config)

       log = get_logger("my-component")
       log.info("started", version="0.1.0")



Functions
---------

.. autoapisummary::

   neurocore.logging.setup.configure_logging
   neurocore.logging.setup.get_logger
   neurocore.logging.setup.reset_logging


Module Contents
---------------

.. py:function:: configure_logging(config: neurocore.config.schema.NeuroCoreConfig) -> None

   Configure structlog and stdlib logging from NeuroCoreConfig.

   Call once at startup. After this, any module can do:

       from neurocore.logging import get_logger
       log = get_logger("skills")
       log.info("skill.loaded", name="neuroweave", version="0.1.0")

   :param config: NeuroCoreConfig with logging.level, logging.format, logging.file.


.. py:function:: get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger

   Get a structlog logger, optionally bound to a component name.

   :param name: Component name (e.g. "skills", "config", "runtime").
                Added as 'component' key in log events.

   :returns: A bound structlog logger.


.. py:function:: reset_logging() -> None

   Reset logging configuration. Primarily for testing.


