"""NeuroCore skill for verifying Lean 4 proof sources.

This skill takes a Lean 4 proof source string, writes it to a temporary
``.lean`` file, invokes the ``lean`` binary with ``--json`` output, and
reports whether the proof was successfully verified.

On success a short certificate ID is generated and stored alongside the
verification result.

Configuration keys (set via ``skill.init(config)``)::

    lean_binary       (str, default "lean")  – path/name of the Lean binary
    mathlib_project   (str)                  – optional path to a Mathlib project dir
    timeout_seconds   (int, default 60)      – subprocess timeout in seconds
    cert_prefix       (str, default "LEAN")  – prefix for the certificate ID

Context keys consumed:

    lean4_proof_source – str  (Lean 4 source code to verify)

Context keys provided:

    lean4_result – dict with keys:
        verified  (bool)       – True iff Lean exited with code 0
        output    (str)        – combined stdout/stderr from Lean
        cert_id   (str | None) – certificate ID when verified, else None
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from uuid import uuid4

from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

__all__ = ["Lean4Skill"]

logger = logging.getLogger(__name__)


class Lean4Skill(AsyncSkill):
    """Verify a Lean 4 proof source by invoking the ``lean`` binary.

    Reads ``lean4_proof_source`` from the context, writes it to a temporary
    ``.lean`` file, runs ``lean --json <file>``, and stores the result in
    ``lean4_result``.

    Config:
        lean_binary (str): Name or path of the Lean binary. Default: ``"lean"``.
        mathlib_project (str): Optional path to a Mathlib project directory.
            When provided the Lean process is launched from that directory so
            that ``lakefile.lean`` / ``lean-toolchain`` are picked up.
        timeout_seconds (int): Subprocess timeout. Default: 60.
        cert_prefix (str): Prefix for generated certificate IDs. Default: ``"LEAN"``.
    """

    skill_meta = SkillMeta(
        name="lean4",
        version="0.1.1",
        description="Verify Lean 4 proof sources using the lean binary",
        provides=["lean4_result"],
        consumes=["lean4_proof_source"],
        tags=["lean4", "formal-verification", "theorem-proving", "mathematics"],
        max_retries=2,
        retry_delay_base=5.0,
        retry_delay_max=60.0,
        config_schema={
            "type": "object",
            "properties": {
                "lean_binary": {"type": "string"},
                "mathlib_project": {"type": "string"},
                "timeout_seconds": {"type": "integer"},
                "cert_prefix": {"type": "string"},
            },
        },
    )

    async def process(self, context: FlowContext) -> FlowContext:
        """Run the Lean verifier on the proof source from context.

        Args:
            context: Flow context; must contain ``lean4_proof_source``.

        Returns:
            Updated context with ``lean4_result`` set.
        """
        source: str = context.get("lean4_proof_source", "")
        if not source.strip():
            logger.warning("Lean4Skill: 'lean4_proof_source' is empty; skipping")
            context.set(
                "lean4_result",
                {"verified": False, "output": "No proof source provided.", "cert_id": None},
            )
            return context

        lean_binary: str = self.config.get("lean_binary", "lean")
        mathlib_project: str | None = self.config.get("mathlib_project") or None
        timeout: int = int(self.config.get("timeout_seconds", 60))
        cert_prefix: str = self.config.get("cert_prefix", "LEAN")

        result = await self._verify(source, lean_binary, mathlib_project, timeout, cert_prefix)
        context.set("lean4_result", result)
        return context

    async def _verify(
        self,
        source: str,
        lean_binary: str,
        mathlib_project: str | None,
        timeout: int,
        cert_prefix: str,
    ) -> dict:
        """Write source to a temp file and invoke Lean.

        Args:
            source: Lean 4 source code.
            lean_binary: Path or name of the ``lean`` executable.
            mathlib_project: Optional directory containing a Mathlib project.
            timeout: Subprocess timeout in seconds.
            cert_prefix: Prefix string for the certificate ID.

        Returns:
            Dict with keys ``verified`` (bool), ``output`` (str),
            ``cert_id`` (str | None).
        """
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".lean", mode="w", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(source)
                tmp_path = tmp.name

            cwd = mathlib_project if mathlib_project else None

            proc = await asyncio.create_subprocess_exec(
                lean_binary,
                "--json",
                tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=cwd,
            )
            try:
                stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                logger.warning("Lean4Skill: lean process timed out after %ds", timeout)
                return {"verified": False, "output": "Lean process timed out.", "cert_id": None}

            output: str = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
            verified: bool = proc.returncode == 0
            cert_id: str | None = None
            if verified:
                cert_id = f"{cert_prefix}-{uuid4().hex[:8].upper()}"
                logger.info("Lean4Skill: proof verified; cert_id=%s", cert_id)
            else:
                logger.info("Lean4Skill: proof NOT verified (exit code %d)", proc.returncode)

            return {"verified": verified, "output": output, "cert_id": cert_id}

        except FileNotFoundError:
            msg = f"Lean binary '{lean_binary}' not found. Is Lean 4 installed?"
            logger.error("Lean4Skill: %s", msg)
            return {"verified": False, "output": msg, "cert_id": None}
        except Exception as exc:
            logger.warning("Lean4Skill: unexpected error: %s", exc)
            return {"verified": False, "output": str(exc), "cert_id": None}
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass
