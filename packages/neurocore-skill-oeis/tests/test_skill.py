"""Tests for OEISSkill."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

from neurocore_skill_oeis import OEISSkill


class TestOEISSkillMetadata:
    def test_skill_meta_is_set(self):
        assert hasattr(OEISSkill, "skill_meta")
        assert isinstance(OEISSkill.skill_meta, SkillMeta)

    def test_skill_meta_name(self):
        assert OEISSkill.skill_meta.name == "oeis"

    def test_skill_provides(self):
        assert "oeis_results" in OEISSkill.skill_meta.provides

    def test_skill_consumes(self):
        assert "oeis_query" in OEISSkill.skill_meta.consumes

    def test_is_async_skill(self):
        assert issubclass(OEISSkill, AsyncSkill)


class TestOEISSkillProcess:
    def _make_skill(self, **config) -> OEISSkill:
        skill = OEISSkill()
        skill.init({"max_results": 5, **config})
        return skill

    def _make_context(self, **kwargs) -> FlowContext:
        ctx = FlowContext()
        for k, v in kwargs.items():
            ctx.set(k, v)
        return ctx

    def test_empty_query_returns_empty_list(self):
        skill = self._make_skill()
        ctx = FlowContext()
        result = asyncio.run(skill.process(ctx))
        assert result.get("oeis_results") == []

    def test_whitespace_query_returns_empty_list(self):
        skill = self._make_skill()
        ctx = self._make_context(oeis_query="   ")
        result = asyncio.run(skill.process(ctx))
        assert result.get("oeis_results") == []

    def test_successful_search(self):
        skill = self._make_skill()
        ctx = self._make_context(oeis_query="fibonacci")

        mock_seq = {
            "number": 45,
            "name": "Fibonacci numbers",
            "data": "0,1,1,2,3,5,8,13,21,34",
        }

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": [mock_seq]}

        async def fake_get(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = fake_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = asyncio.run(skill.process(ctx))

        oeis_results = result.get("oeis_results")
        assert isinstance(oeis_results, list)
        assert len(oeis_results) == 1
        assert oeis_results[0]["number"] == 45

    def test_no_results_returns_empty_list(self):
        skill = self._make_skill()
        ctx = self._make_context(oeis_query="xyzzy_no_match_12345")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": None}

        async def fake_get(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = fake_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = asyncio.run(skill.process(ctx))

        assert result.get("oeis_results") == []

    def test_network_error_never_raises(self):
        skill = self._make_skill()
        ctx = self._make_context(oeis_query="primes")

        async def fake_get(*args, **kwargs):
            raise httpx.RequestError("network unreachable")

        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = fake_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = asyncio.run(skill.process(ctx))

        assert result.get("oeis_results") == []

    def test_max_results_passed_to_api(self):
        skill = self._make_skill(max_results=3)
        ctx = self._make_context(oeis_query="primes")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": []}

        captured_params = {}

        async def fake_get(url, params=None, **kwargs):
            captured_params.update(params or {})
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = fake_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            asyncio.run(skill.process(ctx))

        assert captured_params.get("n") == "3"
        assert captured_params.get("fmt") == "json"
        assert "primes" in captured_params.get("q", "")
