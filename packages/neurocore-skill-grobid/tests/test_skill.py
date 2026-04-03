"""Tests for GrobidSkill."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

from neurocore_skill_grobid import GrobidSkill


class TestGrobidSkillMetadata:
    def test_skill_meta_is_set(self):
        assert hasattr(GrobidSkill, "skill_meta")
        assert isinstance(GrobidSkill.skill_meta, SkillMeta)

    def test_skill_meta_name(self):
        assert GrobidSkill.skill_meta.name == "grobid"

    def test_skill_provides(self):
        assert "grobid_tei" in GrobidSkill.skill_meta.provides

    def test_skill_consumes(self):
        assert "pdf_path" in GrobidSkill.skill_meta.consumes

    def test_is_async_skill(self):
        assert issubclass(GrobidSkill, AsyncSkill)


class TestGrobidSkillConfig:
    def test_requires_grobid_url(self):
        skill = GrobidSkill()
        skill.init({})
        errors = skill.validate_config()
        assert any("grobid_url" in e for e in errors)

    def test_valid_config(self):
        skill = GrobidSkill()
        skill.init({"grobid_url": "http://localhost:8070"})
        errors = skill.validate_config()
        assert errors == []


class TestGrobidSkillProcess:
    def _make_skill(self) -> GrobidSkill:
        skill = GrobidSkill()
        skill.init({"grobid_url": "http://localhost:8070"})
        return skill

    def _make_context(self, **kwargs) -> FlowContext:
        ctx = FlowContext()
        for k, v in kwargs.items():
            ctx.set(k, v)
        return ctx

    def test_missing_pdf_path_returns_empty_string(self):
        skill = self._make_skill()
        ctx = FlowContext()
        result = asyncio.run(skill.process(ctx))
        assert result.get("grobid_tei") == ""

    def test_nonexistent_pdf_returns_empty_string(self):
        skill = self._make_skill()
        ctx = self._make_context(pdf_path="/nonexistent/path/paper.pdf")
        result = asyncio.run(skill.process(ctx))
        assert result.get("grobid_tei") == ""

    def test_successful_extraction(self):
        skill = self._make_skill()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 fake pdf content")
            tmp_path = tmp.name

        ctx = self._make_context(pdf_path=tmp_path)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.text = "<TEI><text>Extracted content</text></TEI>"

        async def fake_post(*args, **kwargs):
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = fake_post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = asyncio.run(skill.process(ctx))

        Path(tmp_path).unlink(missing_ok=True)
        assert result.get("grobid_tei") == "<TEI><text>Extracted content</text></TEI>"

    def test_http_error_returns_empty_string(self):
        skill = self._make_skill()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 fake")
            tmp_path = tmp.name

        ctx = self._make_context(pdf_path=tmp_path)

        async def fake_post(*args, **kwargs):
            raise httpx.RequestError("connection refused")

        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = fake_post
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = asyncio.run(skill.process(ctx))

        Path(tmp_path).unlink(missing_ok=True)
        assert result.get("grobid_tei") == ""
