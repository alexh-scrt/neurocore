"""Tests for ExaSkill."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from flowengine import FlowContext

from neurocore import AsyncSkill, SkillMeta
from neurocore_skill_exa import ExaSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_skill(config: dict[str, Any] | None = None) -> ExaSkill:
    skill = ExaSkill()
    skill.init(config or {"api_key": "test-key"})
    return skill


def _ctx(**kwargs: Any) -> FlowContext:
    ctx = FlowContext()
    for key, value in kwargs.items():
        ctx.set(key, value)
    return ctx


def _make_exa_result(
    title: str = "Result",
    url: str = "https://example.com",
    score: float = 0.9,
) -> MagicMock:
    """Create a mock Exa result object matching the exa-py SearchResult API."""
    r = MagicMock()
    r.title = title
    r.url = url
    r.published_date = "2024-01-01"
    r.author = "Test Author"
    r.score = score
    r.text = None
    r.highlights = None
    return r


def _make_exa_response(results: list[MagicMock] | None = None) -> MagicMock:
    resp = MagicMock()
    resp.results = results or []
    return resp


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------


class TestExaSkillMeta:
    def test_skill_meta_defined(self):
        assert isinstance(ExaSkill.skill_meta, SkillMeta)

    def test_skill_name(self):
        assert ExaSkill.skill_meta.name == "exa"

    def test_provides_exa_results(self):
        assert "exa_results" in ExaSkill.skill_meta.provides

    def test_consumes_exa_query(self):
        assert "exa_query" in ExaSkill.skill_meta.consumes

    def test_is_async_skill(self):
        assert issubclass(ExaSkill, AsyncSkill)

    def test_tags_include_search(self):
        assert "search" in ExaSkill.skill_meta.tags

    def test_config_schema_requires_api_key(self):
        schema = ExaSkill.skill_meta.config_schema
        assert "api_key" in schema.get("required", [])


# ---------------------------------------------------------------------------
# Instantiation tests
# ---------------------------------------------------------------------------


class TestExaSkillInit:
    def test_default_name(self):
        assert ExaSkill().name == "exa"

    def test_custom_name(self):
        assert ExaSkill(name="my-exa").name == "my-exa"

    def test_health_check_after_init(self):
        assert _make_skill().health_check() is True

    def test_health_check_before_init(self):
        assert ExaSkill().health_check() is False

    def test_validate_config_missing_api_key(self):
        skill = ExaSkill()
        skill.init({})
        errors = skill.validate_config()
        assert any("api_key" in e for e in errors)

    def test_validate_config_ok(self):
        errors = _make_skill().validate_config()
        assert errors == []


# ---------------------------------------------------------------------------
# Search mode tests
# ---------------------------------------------------------------------------


class TestExaSkillSearch:
    @pytest.mark.asyncio
    async def test_search_sets_exa_results(self):
        mock_result = _make_exa_result(title="AI paper", url="https://arxiv.org/1")
        mock_response = _make_exa_response([mock_result])

        mock_client = MagicMock()
        mock_client.search_and_contents.return_value = mock_response

        skill = _make_skill({"api_key": "k", "mode": "search", "num_results": 5})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(exa_query="large language models")
            result_ctx = await skill.process(ctx)

        results = result_ctx.get("exa_results")
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["title"] == "AI paper"
        assert results[0]["url"] == "https://arxiv.org/1"

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty(self):
        mock_client = MagicMock()
        skill = _make_skill({"api_key": "k", "mode": "search"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = FlowContext()
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("exa_results") == []
        mock_client.search_and_contents.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_passes_num_results(self):
        mock_client = MagicMock()
        mock_client.search_and_contents.return_value = _make_exa_response()

        skill = _make_skill({"api_key": "k", "mode": "search", "num_results": 20})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(exa_query="query")
            await skill.process(ctx)

        call_kwargs = mock_client.search_and_contents.call_args.kwargs
        assert call_kwargs["num_results"] == 20

    @pytest.mark.asyncio
    async def test_search_passes_category(self):
        mock_client = MagicMock()
        mock_client.search_and_contents.return_value = _make_exa_response()

        skill = _make_skill({"api_key": "k", "mode": "search", "category": "research paper"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(exa_query="quantum computing")
            await skill.process(ctx)

        call_kwargs = mock_client.search_and_contents.call_args.kwargs
        assert call_kwargs.get("category") == "research paper"

    @pytest.mark.asyncio
    async def test_search_include_text_flag(self):
        mock_client = MagicMock()
        mock_client.search_and_contents.return_value = _make_exa_response()

        skill = _make_skill({"api_key": "k", "mode": "search", "include_text": True})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(exa_query="test")
            await skill.process(ctx)

        call_kwargs = mock_client.search_and_contents.call_args.kwargs
        assert call_kwargs.get("text") is True

    @pytest.mark.asyncio
    async def test_search_falls_back_to_plain_search(self):
        """If search_and_contents is absent, plain search() is used."""
        mock_client = MagicMock(spec=["search"])
        mock_client.search.return_value = _make_exa_response()

        skill = _make_skill({"api_key": "k", "mode": "search"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(exa_query="fallback")
            result_ctx = await skill.process(ctx)

        assert isinstance(result_ctx.get("exa_results"), list)
        mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_include_domains_passed(self):
        mock_client = MagicMock()
        mock_client.search_and_contents.return_value = _make_exa_response()

        skill = _make_skill({
            "api_key": "k",
            "mode": "search",
            "include_domains": ["nature.com"],
        })

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(exa_query="biology")
            await skill.process(ctx)

        call_kwargs = mock_client.search_and_contents.call_args.kwargs
        assert "include_domains" in call_kwargs
        assert "nature.com" in call_kwargs["include_domains"]


# ---------------------------------------------------------------------------
# Find similar mode tests
# ---------------------------------------------------------------------------


class TestExaSkillFindSimilar:
    @pytest.mark.asyncio
    async def test_find_similar_uses_exa_query_as_url(self):
        mock_result = _make_exa_result(title="Similar", url="https://similar.com")
        mock_client = MagicMock()
        mock_client.find_similar_and_contents.return_value = _make_exa_response([mock_result])

        skill = _make_skill({"api_key": "k", "mode": "find_similar"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(exa_query="https://seed.com")
            result_ctx = await skill.process(ctx)

        results = result_ctx.get("exa_results")
        assert len(results) == 1
        assert results[0]["title"] == "Similar"

        call_kwargs = mock_client.find_similar_and_contents.call_args.kwargs
        assert call_kwargs["url"] == "https://seed.com"

    @pytest.mark.asyncio
    async def test_find_similar_config_url_takes_priority(self):
        mock_client = MagicMock()
        mock_client.find_similar_and_contents.return_value = _make_exa_response()

        skill = _make_skill({
            "api_key": "k",
            "mode": "find_similar",
            "similarity_url": "https://config-url.com",
        })

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(exa_query="https://context-url.com")
            await skill.process(ctx)

        call_kwargs = mock_client.find_similar_and_contents.call_args.kwargs
        assert call_kwargs["url"] == "https://config-url.com"

    @pytest.mark.asyncio
    async def test_find_similar_no_url_returns_empty(self):
        mock_client = MagicMock()
        skill = _make_skill({"api_key": "k", "mode": "find_similar"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = FlowContext()
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("exa_results") == []
        mock_client.find_similar_and_contents.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_similar_falls_back_to_plain_find_similar(self):
        mock_client = MagicMock(spec=["find_similar"])
        mock_client.find_similar.return_value = _make_exa_response()

        skill = _make_skill({"api_key": "k", "mode": "find_similar"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(exa_query="https://example.com")
            result_ctx = await skill.process(ctx)

        mock_client.find_similar.assert_called_once()
        assert isinstance(result_ctx.get("exa_results"), list)


# ---------------------------------------------------------------------------
# Result serialisation tests
# ---------------------------------------------------------------------------


class TestExaResultSerialisation:
    def test_serialize_basic_fields(self):
        skill = _make_skill()
        r = _make_exa_result(title="Test", url="https://test.com")
        r.score = 0.95
        response = _make_exa_response([r])
        items = skill._serialize_results(response)
        assert len(items) == 1
        assert items[0]["title"] == "Test"
        assert items[0]["url"] == "https://test.com"
        assert items[0]["score"] == 0.95

    def test_serialize_includes_text_when_present(self):
        skill = _make_skill()
        r = _make_exa_result()
        r.text = "Full page text here"
        response = _make_exa_response([r])
        items = skill._serialize_results(response)
        assert items[0]["text"] == "Full page text here"

    def test_serialize_omits_text_when_none(self):
        skill = _make_skill()
        r = _make_exa_result()
        r.text = None
        response = _make_exa_response([r])
        items = skill._serialize_results(response)
        assert "text" not in items[0]

    def test_serialize_empty_results(self):
        skill = _make_skill()
        response = _make_exa_response([])
        items = skill._serialize_results(response)
        assert items == []


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestExaSkillErrorHandling:
    @pytest.mark.asyncio
    async def test_client_build_failure_sets_empty_results(self):
        skill = _make_skill({"api_key": "k", "mode": "search"})

        with patch.object(skill, "_build_client", side_effect=ImportError("exa-py missing")):
            ctx = _ctx(exa_query="test")
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("exa_results") == []

    @pytest.mark.asyncio
    async def test_api_error_sets_empty_results(self):
        mock_client = MagicMock()
        mock_client.search_and_contents.side_effect = Exception("API error")

        skill = _make_skill({"api_key": "k", "mode": "search"})

        with patch.object(skill, "_build_client", return_value=mock_client):
            ctx = _ctx(exa_query="test")
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("exa_results") == []

    @pytest.mark.asyncio
    async def test_invalid_mode_sets_empty_results(self):
        skill = _make_skill({"api_key": "k", "mode": "bad_mode"})
        ctx = _ctx(exa_query="test")
        result_ctx = await skill.process(ctx)
        assert result_ctx.get("exa_results") == []

    @pytest.mark.asyncio
    async def test_never_raises(self):
        skill = _make_skill({"api_key": "k", "mode": "search"})

        with patch.object(skill, "_build_client", side_effect=Exception("boom")):
            ctx = _ctx(exa_query="test")
            result_ctx = await skill.process(ctx)

        assert result_ctx is not None


# ---------------------------------------------------------------------------
# Environment variable fallback
# ---------------------------------------------------------------------------


class TestExaSkillApiKeyEnv:
    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("EXA_API_KEY", "env-key")
        skill = ExaSkill()
        skill.init({})
        assert skill._resolve_api_key() == "env-key"

    def test_config_api_key_takes_priority(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("EXA_API_KEY", "env-key")
        skill = _make_skill({"api_key": "config-key"})
        assert skill._resolve_api_key() == "config-key"
