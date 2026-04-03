"""Tests for UnpaywallSkill."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

from neurocore_skill_unpaywall import UnpaywallSkill


class TestUnpaywallSkillMetadata:
    def test_skill_meta_is_set(self):
        assert hasattr(UnpaywallSkill, "skill_meta")
        assert isinstance(UnpaywallSkill.skill_meta, SkillMeta)

    def test_skill_meta_name(self):
        assert UnpaywallSkill.skill_meta.name == "unpaywall"

    def test_skill_provides(self):
        assert "unpaywall_results" in UnpaywallSkill.skill_meta.provides

    def test_skill_consumes(self):
        assert "dois" in UnpaywallSkill.skill_meta.consumes

    def test_is_async_skill(self):
        assert issubclass(UnpaywallSkill, AsyncSkill)


class TestUnpaywallSkillProcess:
    def _make_skill(self) -> UnpaywallSkill:
        skill = UnpaywallSkill()
        skill.init({"email": "test@example.com"})
        return skill

    def _make_context(self, **kwargs) -> FlowContext:
        ctx = FlowContext()
        for key, value in kwargs.items():
            ctx.set(key, value)
        return ctx

    def test_empty_dois_returns_empty_dict(self):
        skill = self._make_skill()
        ctx = self._make_context(dois=[])
        result = asyncio.run(skill.process(ctx))
        assert result.get("unpaywall_results") == {}

    def test_missing_dois_returns_empty_dict(self):
        skill = self._make_skill()
        ctx = FlowContext()
        result = asyncio.run(skill.process(ctx))
        assert result.get("unpaywall_results") == {}

    def test_successful_fetch(self):
        skill = self._make_skill()
        ctx = self._make_context(dois=["10.1038/nature12373"])

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "best_oa_location": {
                "url_for_pdf": "https://example.com/paper.pdf",
            }
        }

        async def fake_get(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = fake_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = asyncio.run(skill.process(ctx))

        unpaywall_results = result.get("unpaywall_results")
        assert "10.1038/nature12373" in unpaywall_results

    def test_failed_fetch_returns_none(self):
        skill = self._make_skill()
        ctx = self._make_context(dois=["10.9999/invalid"])

        async def fake_get(*args, **kwargs):
            raise httpx.RequestError("connection failed")

        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = fake_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = asyncio.run(skill.process(ctx))

        assert result.get("unpaywall_results") == {"10.9999/invalid": None}

    def test_multiple_dois_concurrent(self):
        skill = self._make_skill()
        dois = ["10.1/a", "10.2/b", "10.3/c"]
        ctx = self._make_context(dois=dois)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"best_oa_location": {"url_for_pdf": "https://pdf.test"}}

        async def fake_get(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = fake_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = asyncio.run(skill.process(ctx))

        results = result.get("unpaywall_results")
        assert set(results.keys()) == set(dois)

    def test_config_schema_requires_email(self):
        skill = UnpaywallSkill()
        skill.init({})
        errors = skill.validate_config()
        assert any("email" in e for e in errors)
