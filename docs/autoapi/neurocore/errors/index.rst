neurocore.errors
================

.. py:module:: neurocore.errors

.. autoapi-nested-parse::

   NeuroCore exception hierarchy.

   All NeuroCore-specific exceptions inherit from NeuroCoreError,
   making it easy to catch framework errors without catching unrelated ones.

   Hierarchy:
       NeuroCoreError
       +-- ConfigError           — configuration loading / validation failures
       +-- SkillError            — skill loading / discovery / execution failures
       +-- BlueprintError        — blueprint parsing / validation failures
       +-- ExecutionError        — runtime execution failures



Exceptions
----------

.. toctree::
   :hidden:

   /autoapi/neurocore/errors/NeuroCoreError
   /autoapi/neurocore/errors/ConfigError
   /autoapi/neurocore/errors/SkillError
   /autoapi/neurocore/errors/BlueprintError
   /autoapi/neurocore/errors/ExecutionError

.. autoapisummary::

   neurocore.errors.NeuroCoreError
   neurocore.errors.ConfigError
   neurocore.errors.SkillError
   neurocore.errors.BlueprintError
   neurocore.errors.ExecutionError


