"""NeuroCore skill for executing SageMath code via the ``sage`` binary.

Two execution modes are supported:

* **eval** – the code snippet is treated as a single expression.  It is
  wrapped in ``print(repr(...))`` before being passed to ``sage -c``.
* **script** – the code is executed verbatim via ``sage -c`` (multi-statement
  scripts, ``print`` calls, etc.).

In both modes the full stdout of the process is captured and written to
``sage_result`` in the context.  The skill never raises; on error the output
will contain the error message from the subprocess.

Configuration keys (set via ``skill.init(config)``)::

    sage_binary       (str, default "sage")   – path/name of the sage binary
    timeout_seconds   (int, default 60)       – subprocess timeout in seconds
    mode              (str, default "eval")   – "eval" | "script"

Context keys consumed:

    sage_code – str  (SageMath source code / expression to evaluate)

Context keys provided:

    sage_result – str  (stdout from the sage process, or error description)
"""

from __future__ import annotations

import asyncio
import logging

from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

__all__ = ["SageMathSkill"]

logger = logging.getLogger(__name__)


class SageMathSkill(AsyncSkill):
    """Execute SageMath code via the ``sage`` binary.

    Reads ``sage_code`` from the context, optionally wraps it for evaluation
    mode, and runs it through ``sage -c <code>``.  Stdout is stored in
    ``sage_result``.

    Config:
        sage_binary (str): Name or path of the ``sage`` executable. Default: ``"sage"``.
        timeout_seconds (int): Subprocess timeout in seconds. Default: 60.
        mode (str): ``"eval"`` (wraps in ``print(repr(...))``) or ``"script"``.
            Default: ``"eval"``.
    """

    skill_meta = SkillMeta(
        name="sagemath",
        version="0.1.0",
        description="Execute SageMath expressions or scripts via the sage binary",
        provides=["sage_result"],
        consumes=["sage_code"],
        tags=["sagemath", "mathematics", "computer-algebra", "symbolic"],
        config_schema={
            "type": "object",
            "properties": {
                "sage_binary": {"type": "string"},
                "timeout_seconds": {"type": "integer"},
                "mode": {"type": "string", "enum": ["eval", "script"]},
            },
        },
    )

    async def process(self, context: FlowContext) -> FlowContext:
        """Run SageMath code from context.

        Args:
            context: Flow context; must contain ``sage_code``.

        Returns:
            Updated context with ``sage_result`` set.
        """
        sage_code: str = context.get("sage_code", "")
        if not sage_code.strip():
            logger.warning("SageMathSkill: 'sage_code' is empty; skipping")
            context.set("sage_result", "")
            return context

        sage_binary: str = self.config.get("sage_binary", "sage")
        timeout: int = int(self.config.get("timeout_seconds", 60))
        mode: str = self.config.get("mode", "eval")

        if mode == "eval":
            # Wrap as a single expression so the result is printed
            code_to_run = f"print(repr({sage_code.strip()}))"
        else:
            code_to_run = sage_code

        result = await self._run_sage(sage_binary, code_to_run, timeout)
        context.set("sage_result", result)
        return context

    async def _run_sage(self, sage_binary: str, code: str, timeout: int) -> str:
        """Launch sage as a subprocess and capture its stdout.

        Args:
            sage_binary: Path or name of the sage executable.
            code: Code string to pass via ``-c``.
            timeout: Maximum time to wait for the process in seconds.

        Returns:
            Stdout output from sage (stripped), or an error description.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                sage_binary,
                "-c",
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                logger.warning("SageMathSkill: sage process timed out after %ds", timeout)
                return f"Error: sage timed out after {timeout} seconds."

            output = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
            return output.strip()

        except FileNotFoundError:
            msg = f"SageMath binary '{sage_binary}' not found. Is SageMath installed?"
            logger.error("SageMathSkill: %s", msg)
            return f"Error: {msg}"
        except Exception as exc:
            logger.warning("SageMathSkill: unexpected error: %s", exc)
            return f"Error: {exc}"
