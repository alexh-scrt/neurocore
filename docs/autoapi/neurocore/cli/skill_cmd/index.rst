neurocore.cli.skill_cmd
=======================

.. py:module:: neurocore.cli.skill_cmd

.. autoapi-nested-parse::

   neurocore skill — list and inspect discovered skills.

   Usage:
       neurocore skill list
       neurocore skill info echo
       neurocore skill info neuroweave --project-root /path/to/project



Attributes
----------

.. autoapisummary::

   neurocore.cli.skill_cmd.console
   neurocore.cli.skill_cmd.skill_app


Functions
---------

.. autoapisummary::

   neurocore.cli.skill_cmd.skill_list
   neurocore.cli.skill_cmd.skill_info


Module Contents
---------------

.. py:data:: console

.. py:data:: skill_app

.. py:function:: skill_list(project_root: Optional[pathlib.Path] = typer.Option(None, '--project-root', '-p', help='Project root directory (auto-detected if not provided).')) -> None

   List all discovered skills.


.. py:function:: skill_info(name: str = typer.Argument(help='Skill name to inspect.'), project_root: Optional[pathlib.Path] = typer.Option(None, '--project-root', '-p', help='Project root directory (auto-detected if not provided).')) -> None

   Show detailed information about a skill.


