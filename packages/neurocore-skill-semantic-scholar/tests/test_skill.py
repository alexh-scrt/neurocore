"""Tests for SemanticScholarSkill.

Covers:
- Skill metadata and instantiation
- search mode: successful response, empty query, HTTP error
- recommendations mode: successful response, empty positive IDs, HTTP error
- citations mode: successful response, missing paper_id config, HTTP error
- Unknown mode handling
- Context key s2_papers always set (never raises)
- API key header injection
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from flowengine import FlowContext

from neurocore_skill_semantic_scholar import SemanticScholarSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    status_code: int = 200,
    json_data: dict[str, Any] | None = None,
) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_error = status_code >= 400
    resp.text = "" if status_code < 400 else "error"
    resp.json.return_value = json_data or {}
    return resp


def _skill_with_config(config: dict[str, Any]) -> SemanticScholarSkill:
    """Instantiate a SemanticScholarSkill and call init() with *config*."""
    skill = SemanticScholarSkill()
    skill.init(config)
    return skill


def _context(**kwargs: Any) -> FlowContext:
    """Build a FlowContext pre-populated with *kwargs*."""
    ctx = FlowContext()
    for key, value in kwargs.items():
        ctx.set(key, value)
    return ctx


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestSkillMeta:
    def test_name(self):
        skill = SemanticScholarSkill()
        assert skill.skill_meta.name == "semantic-scholar"

    def test_version(self):
        skill = SemanticScholarSkill()
        assert skill.skill_meta.version == "0.1.0"

    def test_provides_s2_papers(self):
        skill = SemanticScholarSkill()
        assert "s2_papers" in skill.skill_meta.provides

    def test_consumes_s2_query(self):
        skill = SemanticScholarSkill()
        assert "s2_query" in skill.skill_meta.consumes

    def test_consumes_s2_positive_paper_ids(self):
        skill = SemanticScholarSkill()
        assert "s2_positive_paper_ids" in skill.skill_meta.consumes

    def test_tags_include_research(self):
        skill = SemanticScholarSkill()
        assert "research" in skill.skill_meta.tags

    def test_is_async(self):
        from neurocore import is_async_skill

        skill = SemanticScholarSkill()
        assert is_async_skill(skill)


# ---------------------------------------------------------------------------
# Search mode
# ---------------------------------------------------------------------------


class TestSearchMode:
    @pytest.mark.asyncio
    async def test_search_returns_papers(self):
        papers = [{"paperId": "abc", "title": "Test Paper"}]
        mock_get = AsyncMock(return_value=_make_response(200, {"data": papers}))

        skill = _skill_with_config({"mode": "search"})
        ctx = _context(s2_query="neural networks")

        with patch("httpx.AsyncClient.get", mock_get):
            result = await skill.process(ctx)

        assert result.get("s2_papers") == papers

    @pytest.mark.asyncio
    async def test_search_passes_correct_params(self):
        mock_get = AsyncMock(return_value=_make_response(200, {"data": []}))

        skill = _skill_with_config({"mode": "search", "limit": 5, "fields": "paperId,title"})
        ctx = _context(s2_query="attention mechanism")

        with patch("httpx.AsyncClient.get", mock_get):
            await skill.process(ctx)

        _, kwargs = mock_get.call_args
        params = kwargs.get("params", {})
        assert params["query"] == "attention mechanism"
        assert params["limit"] == 5
        assert params["fields"] == "paperId,title"

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty(self):
        skill = _skill_with_config({"mode": "search"})
        ctx = _context()  # no s2_query

        result = await skill.process(ctx)

        assert result.get("s2_papers") == []

    @pytest.mark.asyncio
    async def test_search_http_error_returns_empty(self):
        mock_get = AsyncMock(return_value=_make_response(500, {}))

        skill = _skill_with_config({"mode": "search"})
        ctx = _context(s2_query="transformers")

        with patch("httpx.AsyncClient.get", mock_get):
            result = await skill.process(ctx)

        assert result.get("s2_papers") == []

    @pytest.mark.asyncio
    async def test_search_network_exception_returns_empty(self):
        import httpx

        mock_get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        skill = _skill_with_config({"mode": "search"})
        ctx = _context(s2_query="transformers")

        with patch("httpx.AsyncClient.get", mock_get):
            result = await skill.process(ctx)

        assert result.get("s2_papers") == []


# ---------------------------------------------------------------------------
# Recommendations mode
# ---------------------------------------------------------------------------


class TestRecommendationsMode:
    @pytest.mark.asyncio
    async def test_recommendations_returns_papers(self):
        papers = [{"paperId": "xyz", "title": "Recommended Paper"}]
        mock_post = AsyncMock(
            return_value=_make_response(200, {"recommendedPapers": papers})
        )

        skill = _skill_with_config({"mode": "recommendations"})
        ctx = _context(s2_positive_paper_ids=["paper1", "paper2"])

        with patch("httpx.AsyncClient.post", mock_post):
            result = await skill.process(ctx)

        assert result.get("s2_papers") == papers

    @pytest.mark.asyncio
    async def test_recommendations_sends_positive_ids(self):
        mock_post = AsyncMock(
            return_value=_make_response(200, {"recommendedPapers": []})
        )

        skill = _skill_with_config({"mode": "recommendations"})
        ctx = _context(s2_positive_paper_ids=["id-abc", "id-def"])

        with patch("httpx.AsyncClient.post", mock_post):
            await skill.process(ctx)

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["positivePaperIds"] == ["id-abc", "id-def"]

    @pytest.mark.asyncio
    async def test_recommendations_empty_ids_returns_empty(self):
        skill = _skill_with_config({"mode": "recommendations"})
        ctx = _context()  # no s2_positive_paper_ids

        result = await skill.process(ctx)

        assert result.get("s2_papers") == []

    @pytest.mark.asyncio
    async def test_recommendations_http_error_returns_empty(self):
        mock_post = AsyncMock(return_value=_make_response(429, {}))

        skill = _skill_with_config({"mode": "recommendations"})
        ctx = _context(s2_positive_paper_ids=["paper1"])

        with patch("httpx.AsyncClient.post", mock_post):
            result = await skill.process(ctx)

        assert result.get("s2_papers") == []


# ---------------------------------------------------------------------------
# Citations mode
# ---------------------------------------------------------------------------


class TestCitationsMode:
    @pytest.mark.asyncio
    async def test_citations_returns_citing_papers(self):
        citing = [
            {"citingPaper": {"paperId": "cit1", "title": "Cites our paper"}},
            {"citingPaper": {"paperId": "cit2", "title": "Also cites it"}},
        ]
        mock_get = AsyncMock(return_value=_make_response(200, {"data": citing}))

        skill = _skill_with_config({"mode": "citations", "paper_id": "target-paper"})
        ctx = _context()

        with patch("httpx.AsyncClient.get", mock_get):
            result = await skill.process(ctx)

        papers = result.get("s2_papers")
        assert len(papers) == 2
        assert papers[0]["paperId"] == "cit1"
        assert papers[1]["paperId"] == "cit2"

    @pytest.mark.asyncio
    async def test_citations_uses_correct_url(self):
        mock_get = AsyncMock(return_value=_make_response(200, {"data": []}))

        skill = _skill_with_config({"mode": "citations", "paper_id": "abc123"})
        ctx = _context()

        with patch("httpx.AsyncClient.get", mock_get):
            await skill.process(ctx)

        call_args = mock_get.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        assert "abc123" in url
        assert "citations" in url

    @pytest.mark.asyncio
    async def test_citations_missing_paper_id_returns_empty(self):
        skill = _skill_with_config({"mode": "citations"})  # no paper_id
        ctx = _context()

        result = await skill.process(ctx)

        assert result.get("s2_papers") == []

    @pytest.mark.asyncio
    async def test_citations_http_error_returns_empty(self):
        mock_get = AsyncMock(return_value=_make_response(404, {}))

        skill = _skill_with_config({"mode": "citations", "paper_id": "bad-id"})
        ctx = _context()

        with patch("httpx.AsyncClient.get", mock_get):
            result = await skill.process(ctx)

        assert result.get("s2_papers") == []


# ---------------------------------------------------------------------------
# Unknown mode
# ---------------------------------------------------------------------------


class TestUnknownMode:
    @pytest.mark.asyncio
    async def test_unknown_mode_returns_empty_and_does_not_raise(self):
        skill = _skill_with_config({"mode": "unsupported"})
        ctx = _context(s2_query="anything")

        result = await skill.process(ctx)

        assert result.get("s2_papers") == []


# ---------------------------------------------------------------------------
# API key injection
# ---------------------------------------------------------------------------


class TestApiKeyHeader:
    @pytest.mark.asyncio
    async def test_api_key_sent_as_header(self):
        mock_get = AsyncMock(return_value=_make_response(200, {"data": []}))

        skill = _skill_with_config({"mode": "search", "api_key": "my-secret-key"})
        ctx = _context(s2_query="deep learning")

        captured_headers: dict[str, str] = {}

        original_init = httpx.AsyncClient.__init__

        def _capture_init(self_inner: Any, **kwargs: Any) -> None:
            captured_headers.update(kwargs.get("headers", {}))
            original_init(self_inner, **kwargs)

        with patch.object(httpx.AsyncClient, "__init__", _capture_init):
            with patch("httpx.AsyncClient.get", mock_get):
                await skill.process(ctx)

        assert captured_headers.get("x-api-key") == "my-secret-key"

    @pytest.mark.asyncio
    async def test_no_api_key_no_header(self):
        mock_get = AsyncMock(return_value=_make_response(200, {"data": []}))

        skill = _skill_with_config({"mode": "search"})
        ctx = _context(s2_query="deep learning")

        captured_headers: dict[str, str] = {}

        original_init = httpx.AsyncClient.__init__

        def _capture_init(self_inner: Any, **kwargs: Any) -> None:
            captured_headers.update(kwargs.get("headers", {}))
            original_init(self_inner, **kwargs)

        with patch.object(httpx.AsyncClient, "__init__", _capture_init):
            with patch("httpx.AsyncClient.get", mock_get):
                await skill.process(ctx)

        assert "x-api-key" not in captured_headers


# ---------------------------------------------------------------------------
# Default field values
# ---------------------------------------------------------------------------


class TestDefaults:
    @pytest.mark.asyncio
    async def test_default_limit_is_10(self):
        mock_get = AsyncMock(return_value=_make_response(200, {"data": []}))

        skill = _skill_with_config({"mode": "search"})
        ctx = _context(s2_query="science")

        with patch("httpx.AsyncClient.get", mock_get):
            await skill.process(ctx)

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["limit"] == 10

    @pytest.mark.asyncio
    async def test_default_fields_contain_title(self):
        mock_get = AsyncMock(return_value=_make_response(200, {"data": []}))

        skill = _skill_with_config({"mode": "search"})
        ctx = _context(s2_query="science")

        with patch("httpx.AsyncClient.get", mock_get):
            await skill.process(ctx)

        _, kwargs = mock_get.call_args
        assert "title" in kwargs["params"]["fields"]
