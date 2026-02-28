neurocore.cli.app
=================

.. py:module:: neurocore.cli.app

.. autoapi-nested-parse::

   NeuroCore CLI application.

   Top-level Typer app that registers all sub-commands.

   Commands:
       neurocore init <name>           — scaffold a new project
       neurocore run <blueprint>       — execute a blueprint
       neurocore skill list            — list discovered skills
       neurocore skill info <name>     — show skill details
       neurocore validate <blueprint>  — validate without executing
       neurocore --version             — show version



Attributes
----------

.. autoapisummary::

   neurocore.cli.app.app


Functions
---------

.. autoapisummary::

   neurocore.cli.app.version_callback
   neurocore.cli.app.main


Module Contents
---------------

.. py:data:: app

.. py:function:: version_callback(value: bool) -> None

   Print version and exit.


.. py:function:: main(version: bool = typer.Option(False, '--version', '-V', help='Show version and exit.', callback=version_callback, is_eager=True)) -> None

   NeuroCore CLI.


