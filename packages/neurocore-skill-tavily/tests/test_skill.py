"""Tests for TavilySkill."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flowengine import FlowContext

from neurocore import AsyncSkill, SkillMeta
from neurocore_skill_tavily import TavilySkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_skill(config: dict[str, Any] | None = None) -> TavilySkill:
    skill = TavilySkill()
    skill.init(config or {"api_key": "test-key"})
    return skill


def _ctx(**kwargs: Any) -> FlowContext:
    ctx = FlowContext()
    for key, value in kwargs.items():
        ctx.set(key, value)
    return ctx


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------


class TestTavilySkillMeta:
    def test_skill_meta_defined(self):
        assert isinstance(TavilySkill.skill_meta, SkillMeta)

    def test_skill_name(self):
        assert TavilySkill.skill_meta.name == "tavily"

    def test_provides_tavily_results(self):
        assert "tavily_results" in TavilySkill.skill_meta.provides

    def test_consumes_tavily_query(self):
        assert "tavily_query" in TavilySkill.skill_meta.consumes

    def test_is_async_skill(self):
        assert issubclass(TavilySkill, AsyncSkill)

    def test_tags_include_search(self):
        assert "search" in TavilySkill.skill_meta.tags


# ---------------------------------------------------------------------------
# Instantiation and config tests
# ---------------------------------------------------------------------------


class TestTavilySkillInit:
    def test_default_name(self):
        skill = TavilySkill()
        assert skill.name == "tavily"

    def test_custom_name(self):
        skill = TavilySkill(name="my-tavily")
        assert skill.name == "my-tavily"

    def test_health_check_after_init(self):
        skill = _make_skill()
        assert skill.health_check() is True

    def test_health_check_before_init(self):
        skill = TavilySkill()
        assert skill.health_check() is False

    def test_config_schema_requires_api_key(self):
        schema = TavilySkill.skill_meta.config_schema
        assert "api_key" in schema.get("required", [])

    def test_validate_config_missing_api_key(self):
        skill = TavilySkill()
        skill.init({})
        errors = skill.validate_config()
        assert any("api_key" in e for e in errors)

    def test_validate_config_ok(self):
        skill = _make_skill()
        errors = skill.validate_config()
        assert errors == []


# ---------------------------------------------------------------------------
# Search mode tests
# ---------------------------------------------------------------------------


class TestTavilySkillSearch:
    @pytest.mark.asyncio
    async def test_search_sets_tavily_results(self):
        fake_results = [{"title": "Result 1", "url": "https://example.com"}]
        fake_response = {"results": fake_results}

        mock_client = MagicMock()
        mock_client.search.return_value = fake_response

        skill = _make_skill({"api_key": "k", "mode": "search", "max_results": 3})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(tavily_query="test query")
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("tavily_results") == fake_results
        mock_client.search.assert_called_once()
        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["query"] == "test query"
        assert call_kwargs["max_results"] == 3

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty(self):
        mock_client = MagicMock()
        skill = _make_skill({"api_key": "k", "mode": "search"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx()  # no tavily_query
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("tavily_results") == []
        mock_client.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_passes_include_domains(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        skill = _make_skill({
            "api_key": "k",
            "mode": "search",
            "include_domains": ["arxiv.org"],
        })

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(tavily_query="quantum computing")
            await skill.process(ctx)

        call_kwargs = mock_client.search.call_args.kwargs
        assert "include_domains" in call_kwargs
        assert "arxiv.org" in call_kwargs["include_domains"]

    @pytest.mark.asyncio
    async def test_search_excludes_exclude_domains(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        skill = _make_skill({
            "api_key": "k",
            "mode": "search",
            "exclude_domains": ["spam.com"],
        })

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(tavily_query="AI")
            await skill.process(ctx)

        call_kwargs = mock_client.search.call_args.kwargs
        assert "exclude_domains" in call_kwargs

    @pytest.mark.asyncio
    async def test_search_no_include_domains_when_empty(self):
        """When include_domains is empty the key should NOT be in the call."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        skill = _make_skill({"api_key": "k", "mode": "search"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(tavily_query="AI")
            await skill.process(ctx)

        call_kwargs = mock_client.search.call_args.kwargs
        assert "include_domains" not in call_kwargs


# ---------------------------------------------------------------------------
# Extract mode tests
# ---------------------------------------------------------------------------


class TestTavilySkillExtract:
    @pytest.mark.asyncio
    async def test_extract_reads_tavily_urls_from_context(self):
        fake_results = [{"url": "https://example.com", "raw_content": "hello"}]
        mock_client = MagicMock()
        mock_client.extract.return_value = {"results": fake_results}

        skill = _make_skill({"api_key": "k", "mode": "extract"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(tavily_urls=["https://example.com"])
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("tavily_results") == fake_results
        mock_client.extract.assert_called_once_with(urls=["https://example.com"])

    @pytest.mark.asyncio
    async def test_extract_falls_back_to_config_urls(self):
        mock_client = MagicMock()
        mock_client.extract.return_value = {"results": []}

        skill = _make_skill({
            "api_key": "k",
            "mode": "extract",
            "urls": ["https://fallback.com"],
        })

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = FlowContext()  # no tavily_urls
            await skill.process(ctx)

        mock_client.extract.assert_called_once_with(urls=["https://fallback.com"])

    @pytest.mark.asyncio
    async def test_extract_empty_urls_returns_empty(self):
        mock_client = MagicMock()
        skill = _make_skill({"api_key": "k", "mode": "extract"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = FlowContext()
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("tavily_results") == []
        mock_client.extract.assert_not_called()


# ---------------------------------------------------------------------------
# Research mode tests
# ---------------------------------------------------------------------------


class TestTavilySkillResearch:
    @pytest.mark.asyncio
    async def test_research_returns_results(self):
        fake_results = [{"title": "Deep result", "url": "https://deep.com"}]
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": fake_results}
        # no qna_search attribute
        del mock_client.qna_search

        skill = _make_skill({"api_key": "k", "mode": "research"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(tavily_query="frontier AI")
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("tavily_results") == fake_results
        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["search_depth"] == "advanced"

    @pytest.mark.asyncio
    async def test_research_uses_qna_search_when_available(self):
        fake_results = [{"title": "Deep result", "url": "https://deep.com"}]
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": fake_results}
        mock_client.qna_search.return_value = "The answer is 42."

        skill = _make_skill({"api_key": "k", "mode": "research"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(tavily_query="meaning of life")
            result_ctx = await skill.process(ctx)

        results = result_ctx.get("tavily_results")
        assert isinstance(results, list)
        # qna answer should be prepended
        assert results[0]["type"] == "answer"
        assert results[0]["content"] == "The answer is 42."

    @pytest.mark.asyncio
    async def test_research_empty_query_returns_empty(self):
        mock_client = MagicMock()
        skill = _make_skill({"api_key": "k", "mode": "research"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = FlowContext()
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("tavily_results") == []


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestTavilySkillErrorHandling:
    @pytest.mark.asyncio
    async def test_client_build_failure_sets_empty_results(self):
        skill = _make_skill({"api_key": "bad-key", "mode": "search"})

        with patch.object(skill, "_build_client", side_effect=RuntimeError("connect failed")):
            ctx = _ctx(tavily_query="anything")
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("tavily_results") == []

    @pytest.mark.asyncio
    async def test_api_error_during_search_sets_empty_results(self):
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("API error")

        skill = _make_skill({"api_key": "k", "mode": "search"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(tavily_query="test")
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("tavily_results") == []

    @pytest.mark.asyncio
    async def test_invalid_mode_sets_empty_results(self):
        skill = _make_skill({"api_key": "k", "mode": "invalid_mode"})
        ctx = _ctx(tavily_query="test")
        result_ctx = await skill.process(ctx)
        assert result_ctx.get("tavily_results") == []

    @pytest.mark.asyncio
    async def test_api_error_during_extract_sets_empty_results(self):
        mock_client = MagicMock()
        mock_client.extract.side_effect = Exception("extract failed")

        skill = _make_skill({"api_key": "k", "mode": "extract"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(tavily_urls=["https://example.com"])
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("tavily_results") == []

    @pytest.mark.asyncio
    async def test_never_raises(self):
        """process() must never raise regardless of errors."""
        skill = _make_skill({"api_key": "k", "mode": "search"})

        with patch.object(skill, "_build_client", side_effect=Exception("boom")):
            ctx = _ctx(tavily_query="test")
            # Should not raise
            result_ctx = await skill.process(ctx)

        assert result_ctx is not None


# ---------------------------------------------------------------------------
# Environment variable fallback
# ---------------------------------------------------------------------------


class TestTavilySkillApiKeyEnv:
    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TAVILY_API_KEY", "env-key")
        skill = TavilySkill()
        skill.init({})  # no api_key in config
        assert skill._resolve_api_key() == "env-key"

    def test_config_api_key_takes_priority(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("TAVILY_API_KEY", "env-key")
        skill = _make_skill({"api_key": "config-key"})
        assert skill._resolve_api_key() == "config-key"
