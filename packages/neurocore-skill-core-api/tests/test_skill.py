"""Tests for CoreApiSkill."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from flowengine import FlowContext

from neurocore import AsyncSkill, SkillMeta
from neurocore_skill_core_api import CoreApiSkill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CORE_SEARCH_URL = "https://api.core.ac.uk/v3/search/works"


def _make_skill(config: dict[str, Any] | None = None) -> CoreApiSkill:
    skill = CoreApiSkill()
    skill.init(config or {"api_key": "test-key"})
    return skill


def _ctx(**kwargs: Any) -> FlowContext:
    ctx = FlowContext()
    for key, value in kwargs.items():
        ctx.set(key, value)
    return ctx


def _core_work(
    id: int = 1,
    title: str = "Test Paper",
    abstract: str = "An abstract.",
    year: int = 2024,
) -> dict[str, Any]:
    return {
        "id": id,
        "title": title,
        "abstract": abstract,
        "yearPublished": year,
        "authors": [{"name": "Alice"}, {"name": "Bob"}],
        "doi": "10.1000/test",
        "downloadUrl": "https://core.ac.uk/download/1.pdf",
        "sourceFulltextUrls": ["https://example.com/paper.pdf"],
        "publisher": "Test Publisher",
        "language": {"name": "English"},
    }


def _core_response(works: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "totalHits": len(works or []),
        "limit": 10,
        "offset": 0,
        "scrollId": None,
        "results": works or [],
    }


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------


class TestCoreApiSkillMeta:
    def test_skill_meta_defined(self):
        assert isinstance(CoreApiSkill.skill_meta, SkillMeta)

    def test_skill_name(self):
        assert CoreApiSkill.skill_meta.name == "core-api"

    def test_provides_core_works(self):
        assert "core_works" in CoreApiSkill.skill_meta.provides

    def test_consumes_core_query(self):
        assert "core_query" in CoreApiSkill.skill_meta.consumes

    def test_is_async_skill(self):
        assert issubclass(CoreApiSkill, AsyncSkill)

    def test_tags_include_research(self):
        assert "research" in CoreApiSkill.skill_meta.tags

    def test_config_schema_requires_api_key(self):
        schema = CoreApiSkill.skill_meta.config_schema
        assert "api_key" in schema.get("required", [])


# ---------------------------------------------------------------------------
# Instantiation tests
# ---------------------------------------------------------------------------


class TestCoreApiSkillInit:
    def test_default_name(self):
        assert CoreApiSkill().name == "core-api"

    def test_custom_name(self):
        assert CoreApiSkill(name="my-core").name == "my-core"

    def test_health_check_after_init(self):
        assert _make_skill().health_check() is True

    def test_health_check_before_init(self):
        assert CoreApiSkill().health_check() is False

    def test_validate_config_missing_api_key(self):
        skill = CoreApiSkill()
        skill.init({})
        errors = skill.validate_config()
        assert any("api_key" in e for e in errors)

    def test_validate_config_ok(self):
        assert _make_skill().validate_config() == []


# ---------------------------------------------------------------------------
# Successful search tests
# ---------------------------------------------------------------------------


class TestCoreApiSkillSearch:
    @pytest.mark.asyncio
    async def test_search_sets_core_works(self):
        work = _core_work(title="Quantum Computing Survey")
        response_data = _core_response([work])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        skill = _make_skill({"api_key": "k", "limit": 5})

        with patch("httpx.AsyncClient", return_value=mock_client):
            ctx = _ctx(core_query="quantum computing")
            result_ctx = await skill.process(ctx)

        works = result_ctx.get("core_works")
        assert isinstance(works, list)
        assert len(works) == 1
        assert works[0]["title"] == "Quantum Computing Survey"
        assert works[0]["authors"] == ["Alice", "Bob"]

    @pytest.mark.asyncio
    async def test_search_passes_correct_params(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _core_response()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        skill = _make_skill({"api_key": "my-key", "limit": 15})

        with patch("httpx.AsyncClient", return_value=mock_client):
            ctx = _ctx(core_query="machine learning")
            await skill.process(ctx)

        call_args = mock_client.get.call_args
        assert call_args.args[0] == _CORE_SEARCH_URL
        params = call_args.kwargs["params"]
        assert params["q"] == "machine learning"
        assert params["limit"] == 15

        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer my-key"

    @pytest.mark.asyncio
    async def test_search_fulltext_param(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _core_response()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        skill = _make_skill({"api_key": "k", "fulltext": True})

        with patch("httpx.AsyncClient", return_value=mock_client):
            ctx = _ctx(core_query="deep learning")
            await skill.process(ctx)

        params = mock_client.get.call_args.kwargs["params"]
        assert params.get("fulltext") == "true"

    @pytest.mark.asyncio
    async def test_fulltext_absent_by_default(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _core_response()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        skill = _make_skill({"api_key": "k"})

        with patch("httpx.AsyncClient", return_value=mock_client):
            ctx = _ctx(core_query="test")
            await skill.process(ctx)

        params = mock_client.get.call_args.kwargs["params"]
        assert "fulltext" not in params

    @pytest.mark.asyncio
    async def test_multiple_works_returned(self):
        works = [_core_work(id=i, title=f"Paper {i}") for i in range(1, 6)]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _core_response(works)
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        skill = _make_skill({"api_key": "k", "limit": 5})

        with patch("httpx.AsyncClient", return_value=mock_client):
            ctx = _ctx(core_query="neural networks")
            result_ctx = await skill.process(ctx)

        works_out = result_ctx.get("core_works")
        assert len(works_out) == 5


# ---------------------------------------------------------------------------
# Work serialisation tests
# ---------------------------------------------------------------------------


class TestCoreApiWorkSerialisation:
    def test_serialize_normalises_fields(self):
        skill = _make_skill()
        raw = _core_work(title="My Paper", year=2023)
        data = {"results": [raw]}
        items = skill._serialize_works(data)
        assert len(items) == 1
        item = items[0]
        assert item["title"] == "My Paper"
        assert item["year"] == 2023
        assert item["authors"] == ["Alice", "Bob"]
        assert item["doi"] == "10.1000/test"
        assert item["language"] == "English"

    def test_serialize_empty_results(self):
        skill = _make_skill()
        items = skill._serialize_works({"results": []})
        assert items == []

    def test_serialize_handles_missing_language(self):
        skill = _make_skill()
        raw = _core_work()
        raw.pop("language")
        items = skill._serialize_works({"results": [raw]})
        assert items[0]["language"] is None

    def test_serialize_includes_fulltext_when_present(self):
        skill = _make_skill()
        raw = _core_work()
        raw["fullText"] = "Full paper text here..."
        items = skill._serialize_works({"results": [raw]})
        assert items[0]["full_text"] == "Full paper text here..."


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestCoreApiSkillErrorHandling:
    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self):
        skill = _make_skill()
        ctx = FlowContext()
        result_ctx = await skill.process(ctx)
        assert result_ctx.get("core_works") == []

    @pytest.mark.asyncio
    async def test_no_api_key_returns_empty(self):
        skill = CoreApiSkill()
        skill.init({})  # empty config, no env var
        ctx = _ctx(core_query="test")

        with patch.dict("os.environ", {}, clear=True):
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("core_works") == []

    @pytest.mark.asyncio
    async def test_http_status_error_sets_empty(self):
        mock_response = MagicMock()
        mock_response.status_code = 403
        http_error = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=mock_response,
        )
        mock_response.raise_for_status.side_effect = http_error

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        skill = _make_skill({"api_key": "bad-key"})

        with patch("httpx.AsyncClient", return_value=mock_client):
            ctx = _ctx(core_query="test")
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("core_works") == []

    @pytest.mark.asyncio
    async def test_request_error_sets_empty(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("connect failed")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        skill = _make_skill({"api_key": "k"})

        with patch("httpx.AsyncClient", return_value=mock_client):
            ctx = _ctx(core_query="test")
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("core_works") == []

    @pytest.mark.asyncio
    async def test_unexpected_error_sets_empty(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("unexpected boom")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        skill = _make_skill({"api_key": "k"})

        with patch("httpx.AsyncClient", return_value=mock_client):
            ctx = _ctx(core_query="test")
            result_ctx = await skill.process(ctx)

        assert result_ctx.get("core_works") == []

    @pytest.mark.asyncio
    async def test_never_raises(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("boom")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        skill = _make_skill({"api_key": "k"})

        with patch("httpx.AsyncClient", return_value=mock_client):
            ctx = _ctx(core_query="test")
            result_ctx = await skill.process(ctx)  # must not raise

        assert result_ctx is not None


# ---------------------------------------------------------------------------
# Environment variable fallback
# ---------------------------------------------------------------------------


class TestCoreApiSkillApiKeyEnv:
    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORE_API_KEY", "env-key")
        skill = CoreApiSkill()
        skill.init({})
        assert skill._resolve_api_key() == "env-key"

    def test_config_api_key_takes_priority(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORE_API_KEY", "env-key")
        skill = _make_skill({"api_key": "config-key"})
        assert skill._resolve_api_key() == "config-key"

    def test_no_key_returns_empty_string(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("CORE_API_KEY", raising=False)
        skill = CoreApiSkill()
        skill.init({})
        assert skill._resolve_api_key() == ""
