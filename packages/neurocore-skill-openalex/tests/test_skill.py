"""Tests for neurocore-skill-openalex — OpenAlexSkill."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta, is_async_skill

from neurocore_skill_openalex import OpenAlexSkill
from neurocore_skill_openalex.skill import _extract_work, _reconstruct_abstract


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_raw_work(**overrides: Any) -> dict[str, Any]:
    """Return a minimal raw OpenAlex work object."""
    base: dict[str, Any] = {
        "id": "https://openalex.org/W12345",
        "doi": "https://doi.org/10.1000/xyz123",
        "title": "Deep Learning for Science",
        "abstract_inverted_index": {"Deep": [0], "Learning": [1], "for": [2], "Science": [3]},
        "publication_date": "2024-01-15",
        "cited_by_count": 42,
        "open_access": {"is_oa": True, "oa_status": "gold"},
        "best_oa_location": {"pdf_url": "https://example.com/paper.pdf"},
        "authorships": [{"author": {"display_name": "Jane Doe"}}],
        "topics": [{"display_name": "Machine Learning"}],
    }
    base.update(overrides)
    return base


def _make_api_response(works: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return a minimal OpenAlex API response envelope."""
    return {
        "meta": {"count": len(works or []), "per_page": 25, "page": 1},
        "results": works or [],
    }


def _make_skill(config: dict[str, Any] | None = None) -> OpenAlexSkill:
    """Create and initialise an OpenAlexSkill instance."""
    skill = OpenAlexSkill()
    skill.init(config or {})
    return skill


# ---------------------------------------------------------------------------
# Unit tests — _reconstruct_abstract helper
# ---------------------------------------------------------------------------

def test_reconstruct_abstract_returns_correct_string():
    inverted = {"hello": [0], "world": [1]}
    assert _reconstruct_abstract(inverted) == "hello world"


def test_reconstruct_abstract_handles_none():
    assert _reconstruct_abstract(None) == ""


def test_reconstruct_abstract_handles_empty_dict():
    assert _reconstruct_abstract({}) == ""


def test_reconstruct_abstract_multi_position():
    inverted = {"the": [0, 4], "cat": [1], "sat": [2], "on": [3], "mat": [5]}
    result = _reconstruct_abstract(inverted)
    words = result.split()
    assert words[0] == "the"
    assert words[1] == "cat"
    assert words[4] == "the"
    assert words[5] == "mat"


# ---------------------------------------------------------------------------
# Unit tests — _extract_work helper
# ---------------------------------------------------------------------------

def test_extract_work_returns_required_keys():
    raw = _make_raw_work()
    work = _extract_work(raw)
    required_keys = {
        "id", "doi", "title", "abstract", "publication_date",
        "cited_by_count", "open_access", "best_oa_location",
        "authorships", "topics",
    }
    assert required_keys == set(work.keys())


def test_extract_work_reconstructs_abstract():
    raw = _make_raw_work(abstract_inverted_index={"hello": [0], "there": [1]})
    work = _extract_work(raw)
    assert work["abstract"] == "hello there"


def test_extract_work_handles_missing_abstract():
    raw = _make_raw_work()
    del raw["abstract_inverted_index"]
    work = _extract_work(raw)
    assert work["abstract"] == ""


def test_extract_work_handles_null_abstract():
    raw = _make_raw_work(abstract_inverted_index=None)
    work = _extract_work(raw)
    assert work["abstract"] == ""


def test_extract_work_preserves_authorships_and_topics():
    raw = _make_raw_work()
    work = _extract_work(raw)
    assert work["authorships"] == raw["authorships"]
    assert work["topics"] == raw["topics"]


def test_extract_work_defaults_missing_lists():
    raw = _make_raw_work()
    del raw["authorships"]
    del raw["topics"]
    work = _extract_work(raw)
    assert work["authorships"] == []
    assert work["topics"] == []


# ---------------------------------------------------------------------------
# Skill identity / metadata tests
# ---------------------------------------------------------------------------

def test_openalex_skill_is_async_skill_subclass():
    assert issubclass(OpenAlexSkill, AsyncSkill)


def test_openalex_skill_process_is_coroutine():
    skill = _make_skill()
    assert is_async_skill(skill)


def test_openalex_skill_meta_name():
    assert OpenAlexSkill.skill_meta.name == "openalex"


def test_openalex_skill_meta_provides():
    assert "openalex_works" in OpenAlexSkill.skill_meta.provides


def test_openalex_skill_meta_consumes():
    assert "openalex_query" in OpenAlexSkill.skill_meta.consumes


def test_openalex_skill_meta_tags():
    tags = OpenAlexSkill.skill_meta.tags
    assert "search" in tags
    assert "papers" in tags


# ---------------------------------------------------------------------------
# Async process() — happy path
# ---------------------------------------------------------------------------

def test_process_sets_openalex_works_on_success():
    """Successful API call writes a list of normalised work dicts."""
    raw_work = _make_raw_work()
    mock_response = MagicMock()
    mock_response.json.return_value = _make_api_response([raw_work])
    mock_response.raise_for_status = MagicMock()

    async def _run():
        skill = _make_skill()
        ctx = FlowContext(data={"openalex_query": "deep learning"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await skill.process(ctx)

        works = result.get("openalex_works")
        assert isinstance(works, list)
        assert len(works) == 1
        work = works[0]
        assert work["id"] == raw_work["id"]
        assert work["doi"] == raw_work["doi"]
        assert work["title"] == raw_work["title"]
        assert work["publication_date"] == raw_work["publication_date"]
        assert work["cited_by_count"] == raw_work["cited_by_count"]

    asyncio.run(_run())


def test_process_sends_query_in_params():
    """The query string is forwarded as the 'search' param."""
    mock_response = MagicMock()
    mock_response.json.return_value = _make_api_response()
    mock_response.raise_for_status = MagicMock()

    async def _run():
        skill = _make_skill()
        ctx = FlowContext(data={"openalex_query": "transformer attention"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await skill.process(ctx)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs.args[1]
        assert params["search"] == "transformer attention"

    asyncio.run(_run())


def test_process_includes_mailto_when_email_configured():
    """When 'email' config is set the mailto param is included."""
    mock_response = MagicMock()
    mock_response.json.return_value = _make_api_response()
    mock_response.raise_for_status = MagicMock()

    async def _run():
        skill = _make_skill({"email": "test@example.com"})
        ctx = FlowContext(data={"openalex_query": "quantum computing"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await skill.process(ctx)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs.args[1]
        assert params.get("mailto") == "test@example.com"

    asyncio.run(_run())


def test_process_omits_mailto_when_email_not_configured():
    """When no email is set the mailto param must be absent."""
    mock_response = MagicMock()
    mock_response.json.return_value = _make_api_response()
    mock_response.raise_for_status = MagicMock()

    async def _run():
        skill = _make_skill()  # no email
        ctx = FlowContext(data={"openalex_query": "neural networks"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await skill.process(ctx)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs.args[1]
        assert "mailto" not in params

    asyncio.run(_run())


def test_process_respects_per_page_config():
    """The per_page config value is forwarded as the per-page param."""
    mock_response = MagicMock()
    mock_response.json.return_value = _make_api_response()
    mock_response.raise_for_status = MagicMock()

    async def _run():
        skill = _make_skill({"per_page": 10})
        ctx = FlowContext(data={"openalex_query": "protein folding"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await skill.process(ctx)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs.args[1]
        assert params["per-page"] == 10

    asyncio.run(_run())


def test_process_respects_filter_config():
    """The filter config value is forwarded as the filter param."""
    mock_response = MagicMock()
    mock_response.json.return_value = _make_api_response()
    mock_response.raise_for_status = MagicMock()

    async def _run():
        skill = _make_skill({"filter": "type:article,open_access.is_oa:true"})
        ctx = FlowContext(data={"openalex_query": "CRISPR"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await skill.process(ctx)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs.args[1]
        assert params["filter"] == "type:article,open_access.is_oa:true"

    asyncio.run(_run())


def test_process_respects_sort_config():
    """The sort config value is forwarded as the sort param."""
    mock_response = MagicMock()
    mock_response.json.return_value = _make_api_response()
    mock_response.raise_for_status = MagicMock()

    async def _run():
        skill = _make_skill({"sort": "cited_by_count:desc"})
        ctx = FlowContext(data={"openalex_query": "climate change"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await skill.process(ctx)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs.args[1]
        assert params["sort"] == "cited_by_count:desc"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Async process() — failure / edge-case behaviour
# ---------------------------------------------------------------------------

def test_process_returns_empty_list_on_http_status_error():
    """HTTP 4xx/5xx errors must set openalex_works to [] without raising."""
    import httpx as _httpx

    async def _run():
        skill = _make_skill()
        ctx = FlowContext(data={"openalex_query": "test"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            error_response = MagicMock()
            error_response.status_code = 429
            mock_client.get = AsyncMock(
                side_effect=_httpx.HTTPStatusError(
                    "rate limited",
                    request=MagicMock(),
                    response=error_response,
                )
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await skill.process(ctx)

        assert result.get("openalex_works") == []

    asyncio.run(_run())


def test_process_returns_empty_list_on_request_error():
    """Network errors must set openalex_works to [] without raising."""
    import httpx as _httpx

    async def _run():
        skill = _make_skill()
        ctx = FlowContext(data={"openalex_query": "test"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=_httpx.ConnectError("connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await skill.process(ctx)

        assert result.get("openalex_works") == []

    asyncio.run(_run())


def test_process_returns_empty_list_on_unexpected_exception():
    """Any unexpected exception must set openalex_works to [] without raising."""

    async def _run():
        skill = _make_skill()
        ctx = FlowContext(data={"openalex_query": "test"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=RuntimeError("unexpected"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await skill.process(ctx)

        assert result.get("openalex_works") == []

    asyncio.run(_run())


def test_process_returns_empty_list_when_query_is_absent():
    """Missing openalex_query key must produce an empty result list."""

    async def _run():
        skill = _make_skill()
        ctx = FlowContext(data={})  # no query key
        result = await skill.process(ctx)
        assert result.get("openalex_works") == []

    asyncio.run(_run())


def test_process_returns_empty_list_when_query_is_empty_string():
    """An empty string query must produce an empty result list."""

    async def _run():
        skill = _make_skill()
        ctx = FlowContext(data={"openalex_query": "   "})
        result = await skill.process(ctx)
        assert result.get("openalex_works") == []

    asyncio.run(_run())


def test_process_returns_empty_list_when_results_is_absent():
    """If the API payload has no 'results' key, return an empty list."""
    mock_response = MagicMock()
    mock_response.json.return_value = {}  # no 'results' key
    mock_response.raise_for_status = MagicMock()

    async def _run():
        skill = _make_skill()
        ctx = FlowContext(data={"openalex_query": "topology"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await skill.process(ctx)

        assert result.get("openalex_works") == []

    asyncio.run(_run())


def test_process_returns_context_unchanged_on_error():
    """On failure the context must retain any data that was already present."""
    import httpx as _httpx

    async def _run():
        skill = _make_skill()
        ctx = FlowContext(data={"openalex_query": "test", "existing_key": "keep me"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=_httpx.ConnectError("down")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await skill.process(ctx)

        assert result.get("existing_key") == "keep me"
        assert result.get("openalex_works") == []

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# select / field projection
# ---------------------------------------------------------------------------

def test_process_uses_default_select_when_not_configured():
    """Default select includes all required output fields."""
    mock_response = MagicMock()
    mock_response.json.return_value = _make_api_response()
    mock_response.raise_for_status = MagicMock()

    async def _run():
        skill = _make_skill()
        ctx = FlowContext(data={"openalex_query": "dark matter"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await skill.process(ctx)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs.args[1]
        select_param: str = params["select"]
        for field in ("id", "doi", "title", "abstract_inverted_index",
                      "publication_date", "cited_by_count"):
            assert field in select_param


def test_process_respects_custom_select_config():
    """A custom select list is forwarded as a comma-joined string."""
    mock_response = MagicMock()
    mock_response.json.return_value = _make_api_response()
    mock_response.raise_for_status = MagicMock()

    async def _run():
        skill = _make_skill({"select": ["id", "title", "doi"]})
        ctx = FlowContext(data={"openalex_query": "exoplanets"})
        with patch(
            "neurocore_skill_openalex.skill.httpx.AsyncClient",
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await skill.process(ctx)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs.args[1]
        assert params["select"] == "id,title,doi"

    asyncio.run(_run())
