neurocore.cli.validate_cmd
==========================

.. py:module:: neurocore.cli.validate_cmd

.. autoapi-nested-parse::

   neurocore validate — validate a blueprint without executing.

   Checks that:
   1. The YAML file parses correctly
   2. The blueprint structure is valid
   3. All referenced skills are discovered and registered

   Usage:
       neurocore validate blueprints/agent.flow.yaml
       neurocore validate flow.yaml --project-root /path/to/project



Attributes
----------

.. autoapisummary::

   neurocore.cli.validate_cmd.console


Functions
---------

.. autoapisummary::

   neurocore.cli.validate_cmd.validate_blueprint_cmd


Module Contents
---------------

.. py:data:: console

.. py:function:: validate_blueprint_cmd(blueprint: pathlib.Path = typer.Argument(help='Path to the blueprint YAML file to validate.', exists=True, dir_okay=False, readable=True), project_root: Optional[pathlib.Path] = typer.Option(None, '--project-root', '-p', help='Project root directory (auto-detected if not provided).')) -> None

   Validate a blueprint without executing it.


