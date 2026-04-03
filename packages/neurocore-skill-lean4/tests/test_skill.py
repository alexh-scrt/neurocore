"""Tests for Lean4Skill."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

from neurocore_skill_lean4 import Lean4Skill


class TestLean4SkillMetadata:
    def test_skill_meta_is_set(self):
        assert hasattr(Lean4Skill, "skill_meta")
        assert isinstance(Lean4Skill.skill_meta, SkillMeta)

    def test_skill_meta_name(self):
        assert Lean4Skill.skill_meta.name == "lean4"

    def test_skill_provides(self):
        assert "lean4_result" in Lean4Skill.skill_meta.provides

    def test_skill_consumes(self):
        assert "lean4_proof_source" in Lean4Skill.skill_meta.consumes

    def test_is_async_skill(self):
        assert issubclass(Lean4Skill, AsyncSkill)


class TestLean4SkillProcess:
    def _make_skill(self, **config) -> Lean4Skill:
        skill = Lean4Skill()
        skill.init({"lean_binary": "lean", "cert_prefix": "TEST", **config})
        return skill

    def _make_context(self, **kwargs) -> FlowContext:
        ctx = FlowContext()
        for k, v in kwargs.items():
            ctx.set(k, v)
        return ctx

    def test_empty_source_skips(self):
        skill = self._make_skill()
        ctx = FlowContext()
        result = asyncio.run(skill.process(ctx))
        lean4_result = result.get("lean4_result")
        assert lean4_result["verified"] is False
        assert lean4_result["cert_id"] is None

    def test_whitespace_source_skips(self):
        skill = self._make_skill()
        ctx = self._make_context(lean4_proof_source="   \n  ")
        result = asyncio.run(skill.process(ctx))
        assert result.get("lean4_result")["verified"] is False

    def test_verified_proof_generates_cert_id(self):
        skill = self._make_skill(cert_prefix="MYTEST")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.kill = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", None))

        async def fake_create_subprocess_exec(*args, **kwargs):
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=fake_create_subprocess_exec):
            ctx = self._make_context(lean4_proof_source="#check Nat.add_comm")
            result = asyncio.run(skill.process(ctx))

        lean4_result = result.get("lean4_result")
        assert lean4_result["verified"] is True
        assert lean4_result["cert_id"] is not None
        assert lean4_result["cert_id"].startswith("MYTEST-")
        assert len(lean4_result["cert_id"]) == len("MYTEST-") + 8

    def test_failed_proof_no_cert_id(self):
        skill = self._make_skill()

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.kill = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"error: unknown identifier", None))

        async def fake_create_subprocess_exec(*args, **kwargs):
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=fake_create_subprocess_exec):
            ctx = self._make_context(lean4_proof_source="#check BadIdent")
            result = asyncio.run(skill.process(ctx))

        lean4_result = result.get("lean4_result")
        assert lean4_result["verified"] is False
        assert lean4_result["cert_id"] is None

    def test_lean_binary_not_found_never_raises(self):
        skill = self._make_skill(lean_binary="/nonexistent/lean")
        ctx = self._make_context(lean4_proof_source="#check Nat")

        async def fake_exec(*args, **kwargs):
            raise FileNotFoundError("lean not found")

        with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            result = asyncio.run(skill.process(ctx))

        lean4_result = result.get("lean4_result")
        assert lean4_result["verified"] is False
        assert lean4_result["cert_id"] is None
        assert "not found" in lean4_result["output"]

    def test_timeout_never_raises(self):
        skill = self._make_skill(timeout_seconds=1)

        mock_proc = MagicMock()
        mock_proc.returncode = None
        mock_proc.kill = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", None))

        async def fake_communicate():
            raise asyncio.TimeoutError()

        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        async def fake_exec(*args, **kwargs):
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
                ctx = self._make_context(lean4_proof_source="#check Nat")
                result = asyncio.run(skill.process(ctx))

        lean4_result = result.get("lean4_result")
        assert lean4_result["verified"] is False
        assert "timed out" in lean4_result["output"]
