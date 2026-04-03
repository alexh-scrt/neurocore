"""NeuroCore skill for symbolic mathematics via SymPy.

Reads a SymPy expression string from the flow context, evaluates it inside a
sandboxed namespace (only SymPy symbols and functions are available), and
stores the string representation of the result.  Evaluation runs in a thread
executor so it does not block the asyncio event loop.

Configuration keys (set via ``skill.init(config)``)::

    timeout_seconds (int, default 30) – wall-clock limit for the evaluation

Context keys consumed:

    sympy_expression – str  (e.g. ``"integrate(x**2, x)"`` or ``"factor(x**2 - 1)"``)

Context keys provided:

    sympy_result – dict with keys:
        value (str)        – string representation of the result, or "" on error
        error (str | None) – error message, or None when successful
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from typing import Any

from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

__all__ = ["SympySkill"]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sandboxed namespace – only whitelisted SymPy names are available to the
# evaluated expression.  No builtins, no imports.
# ---------------------------------------------------------------------------

def _build_sympy_namespace() -> dict[str, Any]:
    """Build a restricted namespace populated with common SymPy names.

    Returns:
        Dictionary mapping name -> SymPy object (or safe builtin).
    """
    import sympy  # local import so the module loads without sympy installed

    namespace: dict[str, Any] = {
        # Core
        "__builtins__": {},  # no builtins
        # Symbols
        "symbols": sympy.symbols,
        "Symbol": sympy.Symbol,
        "Dummy": sympy.Dummy,
        # Numbers
        "Integer": sympy.Integer,
        "Float": sympy.Float,
        "Rational": sympy.Rational,
        "pi": sympy.pi,
        "E": sympy.E,
        "I": sympy.I,
        "oo": sympy.oo,
        "zoo": sympy.zoo,
        "nan": sympy.nan,
        # Common functions
        "sin": sympy.sin,
        "cos": sympy.cos,
        "tan": sympy.tan,
        "asin": sympy.asin,
        "acos": sympy.acos,
        "atan": sympy.atan,
        "atan2": sympy.atan2,
        "sinh": sympy.sinh,
        "cosh": sympy.cosh,
        "tanh": sympy.tanh,
        "exp": sympy.exp,
        "log": sympy.log,
        "ln": sympy.log,
        "sqrt": sympy.sqrt,
        "Abs": sympy.Abs,
        "sign": sympy.sign,
        "floor": sympy.floor,
        "ceiling": sympy.ceiling,
        # Calculus
        "diff": sympy.diff,
        "integrate": sympy.integrate,
        "limit": sympy.limit,
        "series": sympy.series,
        # Algebra
        "factor": sympy.factor,
        "expand": sympy.expand,
        "simplify": sympy.simplify,
        "cancel": sympy.cancel,
        "collect": sympy.collect,
        "apart": sympy.apart,
        "together": sympy.together,
        "solve": sympy.solve,
        "solveset": sympy.solveset,
        "roots": sympy.roots,
        "groebner": sympy.groebner,
        # Linear algebra
        "Matrix": sympy.Matrix,
        "eye": sympy.eye,
        "zeros": sympy.zeros,
        "ones": sympy.ones,
        # Number theory
        "gcd": sympy.gcd,
        "lcm": sympy.lcm,
        "isprime": sympy.isprime,
        "factorint": sympy.factorint,
        # Combinatorics / misc
        "binomial": sympy.binomial,
        "factorial": sympy.factorial,
        "Sum": sympy.Sum,
        "Product": sympy.Product,
        "Piecewise": sympy.Piecewise,
        "Eq": sympy.Eq,
        "Ne": sympy.Ne,
        "Lt": sympy.Lt,
        "Le": sympy.Le,
        "Gt": sympy.Gt,
        "Ge": sympy.Ge,
        # Pretty printing helpers
        "latex": sympy.latex,
        "pretty": sympy.pretty,
    }
    return namespace


def _evaluate_sympy(expression: str) -> dict[str, Any]:
    """Evaluate a SymPy expression string in a sandboxed namespace.

    Args:
        expression: A SymPy expression as a Python string.

    Returns:
        Dict with keys ``value`` (str) and ``error`` (str | None).
    """
    namespace = _build_sympy_namespace()
    try:
        result = eval(expression, namespace)  # noqa: S307
        return {"value": str(result), "error": None}
    except Exception as exc:
        return {"value": "", "error": str(exc)}


class SympySkill(AsyncSkill):
    """Evaluate a SymPy expression string in a sandboxed namespace.

    The expression is evaluated in a thread executor (so the event loop is not
    blocked by long symbolic computations).  A timeout guards against
    pathological inputs.

    Config:
        timeout_seconds (int): Maximum seconds to wait for evaluation. Default: 30.
    """

    skill_meta = SkillMeta(
        name="sympy",
        version="0.1.1",
        description="Evaluate symbolic mathematics expressions via SymPy",
        provides=["sympy_result"],
        consumes=["sympy_expression"],
        tags=["sympy", "mathematics", "symbolic", "algebra", "calculus"],
        max_retries=2,
        retry_delay_base=1.0,
        retry_delay_max=30.0,
        config_schema={
            "type": "object",
            "properties": {
                "timeout_seconds": {"type": "integer"},
            },
        },
    )

    async def process(self, context: FlowContext) -> FlowContext:
        """Evaluate the SymPy expression from context.

        Args:
            context: Flow context; must contain ``sympy_expression``.

        Returns:
            Updated context with ``sympy_result`` set.
        """
        expression: str = context.get("sympy_expression", "")
        if not expression.strip():
            logger.warning("SympySkill: 'sympy_expression' is empty; skipping")
            context.set("sympy_result", {"value": "", "error": "No expression provided."})
            return context

        timeout: int = int(self.config.get("timeout_seconds", 30))

        loop = asyncio.get_event_loop()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = loop.run_in_executor(executor, _evaluate_sympy, expression.strip())
                result: dict[str, Any] = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("SympySkill: evaluation timed out after %ds", timeout)
            result = {
                "value": "",
                "error": f"Evaluation timed out after {timeout} seconds.",
            }
        except Exception as exc:
            logger.warning("SympySkill: unexpected error: %s", exc)
            result = {"value": "", "error": str(exc)}

        context.set("sympy_result", result)
        return context
