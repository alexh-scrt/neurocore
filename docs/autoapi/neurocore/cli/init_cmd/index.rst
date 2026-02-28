neurocore.cli.init_cmd
======================

.. py:module:: neurocore.cli.init_cmd

.. autoapi-nested-parse::

   neurocore init — scaffold a new project.

   Creates a new NeuroCore project with:
   - neurocore.yaml (configuration)
   - .env.example (environment template)
   - blueprints/ directory with example blueprint
   - skills/ directory
   - data/ directory
   - logs/ directory

   Usage:
       neurocore init my-agent
       neurocore init my-agent --dir /path/to/projects



Attributes
----------

.. autoapisummary::

   neurocore.cli.init_cmd.console


Functions
---------

.. autoapisummary::

   neurocore.cli.init_cmd.init_project


Module Contents
---------------

.. py:data:: console

.. py:function:: init_project(name: str = typer.Argument(help='Project name (used for directory and config).'), directory: pathlib.Path = typer.Option(Path('.'), '--dir', '-d', help='Parent directory to create the project in.')) -> None

   Scaffold a new NeuroCore project.


