"""Tests for SympySkill."""

from __future__ import annotations

import asyncio

import pytest
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

from neurocore_skill_sympy import SympySkill


class TestSympySkillMetadata:
    def test_skill_meta_is_set(self):
        assert hasattr(SympySkill, "skill_meta")
        assert isinstance(SympySkill.skill_meta, SkillMeta)

    def test_skill_meta_name(self):
        assert SympySkill.skill_meta.name == "sympy"

    def test_skill_provides(self):
        assert "sympy_result" in SympySkill.skill_meta.provides

    def test_skill_consumes(self):
        assert "sympy_expression" in SympySkill.skill_meta.consumes

    def test_is_async_skill(self):
        assert issubclass(SympySkill, AsyncSkill)


class TestSympySkillProcess:
    def _make_skill(self, **config) -> SympySkill:
        skill = SympySkill()
        skill.init({"timeout_seconds": 10, **config})
        return skill

    def _make_context(self, **kwargs) -> FlowContext:
        ctx = FlowContext()
        for k, v in kwargs.items():
            ctx.set(k, v)
        return ctx

    def test_empty_expression_returns_error(self):
        skill = self._make_skill()
        ctx = FlowContext()
        result = asyncio.run(skill.process(ctx))
        sympy_result = result.get("sympy_result")
        assert sympy_result["value"] == ""
        assert sympy_result["error"] is not None

    def test_simple_arithmetic(self):
        skill = self._make_skill()
        ctx = self._make_context(sympy_expression="Integer(2) + Integer(2)")
        result = asyncio.run(skill.process(ctx))
        sympy_result = result.get("sympy_result")
        assert sympy_result["error"] is None
        assert sympy_result["value"] == "4"

    def test_symbolic_derivative(self):
        skill = self._make_skill()
        ctx = self._make_context(sympy_expression="diff(symbols('x')**3, symbols('x'))")
        result = asyncio.run(skill.process(ctx))
        sympy_result = result.get("sympy_result")
        assert sympy_result["error"] is None
        assert "x**2" in sympy_result["value"] or "3*x**2" in sympy_result["value"]

    def test_factorial(self):
        skill = self._make_skill()
        ctx = self._make_context(sympy_expression="factorial(10)")
        result = asyncio.run(skill.process(ctx))
        sympy_result = result.get("sympy_result")
        assert sympy_result["error"] is None
        assert sympy_result["value"] == "3628800"

    def test_invalid_expression_returns_error(self):
        skill = self._make_skill()
        ctx = self._make_context(sympy_expression="undefined_function_xyz()")
        result = asyncio.run(skill.process(ctx))
        sympy_result = result.get("sympy_result")
        assert sympy_result["error"] is not None
        assert sympy_result["value"] == ""

    def test_sandbox_blocks_builtins(self):
        """The sandboxed namespace must not expose dangerous builtins like open()."""
        skill = self._make_skill()
        ctx = self._make_context(sympy_expression="open('/etc/passwd')")
        result = asyncio.run(skill.process(ctx))
        sympy_result = result.get("sympy_result")
        # Should error because __builtins__ is empty
        assert sympy_result["error"] is not None

    def test_sandbox_blocks_import(self):
        """The sandboxed namespace must not expose __import__."""
        skill = self._make_skill()
        ctx = self._make_context(sympy_expression="__import__('os').system('id')")
        result = asyncio.run(skill.process(ctx))
        sympy_result = result.get("sympy_result")
        assert sympy_result["error"] is not None

    def test_timeout_never_raises(self):
        """A timeout must result in an error dict, not an exception."""
        import concurrent.futures
        from unittest.mock import patch

        skill = self._make_skill(timeout_seconds=1)
        ctx = self._make_context(sympy_expression="Integer(1) + Integer(1)")

        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            result = asyncio.run(skill.process(ctx))

        sympy_result = result.get("sympy_result")
        assert sympy_result["error"] is not None
        assert "timed out" in sympy_result["error"].lower()
