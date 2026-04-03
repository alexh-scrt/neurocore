"""Tests for SageMathSkill."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

from neurocore_skill_sagemath import SageMathSkill


class TestSageMathSkillMetadata:
    def test_skill_meta_is_set(self):
        assert hasattr(SageMathSkill, "skill_meta")
        assert isinstance(SageMathSkill.skill_meta, SkillMeta)

    def test_skill_meta_name(self):
        assert SageMathSkill.skill_meta.name == "sagemath"

    def test_skill_provides(self):
        assert "sage_result" in SageMathSkill.skill_meta.provides

    def test_skill_consumes(self):
        assert "sage_code" in SageMathSkill.skill_meta.consumes

    def test_is_async_skill(self):
        assert issubclass(SageMathSkill, AsyncSkill)


class TestSageMathSkillProcess:
    def _make_skill(self, **config) -> SageMathSkill:
        skill = SageMathSkill()
        skill.init({"sage_binary": "sage", **config})
        return skill

    def _make_context(self, **kwargs) -> FlowContext:
        ctx = FlowContext()
        for k, v in kwargs.items():
            ctx.set(k, v)
        return ctx

    def test_empty_code_returns_empty_string(self):
        skill = self._make_skill()
        ctx = FlowContext()
        result = asyncio.run(skill.process(ctx))
        assert result.get("sage_result") == ""

    def test_whitespace_code_returns_empty_string(self):
        skill = self._make_skill()
        ctx = self._make_context(sage_code="  \n  ")
        result = asyncio.run(skill.process(ctx))
        assert result.get("sage_result") == ""

    def test_eval_mode_wraps_in_print_repr(self):
        skill = self._make_skill(mode="eval")
        ctx = self._make_context(sage_code="1 + 1")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.kill = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"2\n", None))

        captured_args = []

        async def fake_exec(*args, **kwargs):
            captured_args.extend(args)
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            result = asyncio.run(skill.process(ctx))

        assert result.get("sage_result") == "2"
        # Verify eval mode wraps with print(repr(...))
        assert "print(repr(" in captured_args[-1]

    def test_script_mode_passes_code_verbatim(self):
        skill = self._make_skill(mode="script")
        ctx = self._make_context(sage_code="for i in range(3):\n    print(i)")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.kill = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"0\n1\n2\n", None))

        captured_args = []

        async def fake_exec(*args, **kwargs):
            captured_args.extend(args)
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            result = asyncio.run(skill.process(ctx))

        assert result.get("sage_result") == "0\n1\n2"
        assert "print(repr(" not in captured_args[-1]

    def test_binary_not_found_never_raises(self):
        skill = self._make_skill(sage_binary="/nonexistent/sage")
        ctx = self._make_context(sage_code="1+1")

        async def fake_exec(*args, **kwargs):
            raise FileNotFoundError("sage not found")

        with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            result = asyncio.run(skill.process(ctx))

        sage_result = result.get("sage_result")
        assert "Error" in sage_result
        assert "not found" in sage_result

    def test_timeout_never_raises(self):
        skill = self._make_skill(timeout_seconds=1)

        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.kill = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", None))

        async def fake_exec(*args, **kwargs):
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
                ctx = self._make_context(sage_code="while True: pass")
                result = asyncio.run(skill.process(ctx))

        sage_result = result.get("sage_result")
        assert "timed out" in sage_result.lower()
