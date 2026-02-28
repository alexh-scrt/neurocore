neurocore.cli.run_cmd
=====================

.. py:module:: neurocore.cli.run_cmd

.. autoapi-nested-parse::

   neurocore run — execute a blueprint via FlowEngine.

   Loads configuration, discovers skills, parses the blueprint, and
   executes through FlowEngine. Outputs the final context data.

   Usage:
       neurocore run blueprints/agent.flow.yaml
       neurocore run flow.yaml --data input=hello --data count=5
       neurocore run flow.yaml --project-root /path/to/project



Attributes
----------

.. autoapisummary::

   neurocore.cli.run_cmd.console
   neurocore.cli.run_cmd.output_console


Functions
---------

.. autoapisummary::

   neurocore.cli.run_cmd.run_blueprint


Module Contents
---------------

.. py:data:: console

.. py:data:: output_console

.. py:function:: run_blueprint(blueprint: pathlib.Path = typer.Argument(help='Path to the blueprint YAML file.', exists=True, dir_okay=False, readable=True), data: list[str] = typer.Option([], '--data', '-d', help='Initial context data as KEY=VALUE pairs.'), project_root: Optional[pathlib.Path] = typer.Option(None, '--project-root', '-p', help='Project root directory (auto-detected if not provided).'), output_json: bool = typer.Option(False, '--json', '-j', help='Output result as JSON.'), verbose: bool = typer.Option(False, '--verbose', '-v', help='Show detailed execution info.')) -> None

   Execute a blueprint via FlowEngine.


