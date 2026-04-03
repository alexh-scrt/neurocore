"""Tests for ArxivSkill.

Strategy
--------
The ``arxiv`` library makes real HTTP calls which would be slow and flaky in
unit tests.  We patch ``arxiv.Client.results`` (the synchronous generator that
backs every search) and ``arxiv.Search`` so every test runs offline.

The ``MockProvider`` pattern from ``neurocore.llm.provider`` is referenced for
completeness (ArxivSkill does not use an LLM, so we import it only to show the
pattern is available and consistent with the wider project).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from flowengine import FlowContext

from neurocore import AsyncSkill, SkillMeta

# We import the skill itself; all arxiv calls will be patched.
from neurocore_skill_arxiv import ArxivSkill
from neurocore_skill_arxiv.skill import _get_sort_criterion


# ---------------------------------------------------------------------------
# Helpers — fake arxiv result objects
# ---------------------------------------------------------------------------


def _make_arxiv_result(
    *,
    entry_id: str = "https://arxiv.org/abs/2401.00001",
    title: str = "Test Paper",
    summary: str = "This is an abstract.",
    authors: list[str] | None = None,
    categories: list[str] | None = None,
    published: datetime | None = None,
    updated: datetime | None = None,
    pdf_url: str = "https://arxiv.org/pdf/2401.00001",
) -> MagicMock:
    """Build a MagicMock that mimics an ``arxiv.Result``."""
    result = MagicMock()
    result.entry_id = entry_id
    result.title = title
    result.summary = summary
    result.authors = [MagicMock(__str__=lambda self: a) for a in (authors or ["Alice", "Bob"])]
    result.categories = categories or ["cs.LG", "cs.AI"]
    result.published = published or datetime(2024, 1, 15, tzinfo=timezone.utc)
    result.updated = updated or datetime(2024, 1, 20, tzinfo=timezone.utc)
    result.pdf_url = pdf_url
    return result


def _make_skill(config: dict[str, Any] | None = None) -> ArxivSkill:
    """Instantiate and initialise an ArxivSkill with *config*."""
    skill = ArxivSkill()
    skill.init(config or {})
    return skill


# ---------------------------------------------------------------------------
# Fixture — a pre-built fake result for reuse
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_result() -> MagicMock:
    return _make_arxiv_result()


@pytest.fixture
def skill() -> ArxivSkill:
    return _make_skill()


# ---------------------------------------------------------------------------
# Smoke tests — class structure
# ---------------------------------------------------------------------------


class TestArxivSkillMeta:
    def test_is_async_skill(self):
        assert issubclass(ArxivSkill, AsyncSkill)

    def test_skill_meta_name(self):
        assert ArxivSkill.skill_meta.name == "arxiv"

    def test_skill_meta_version(self):
        assert ArxivSkill.skill_meta.version == "0.1.0"

    def test_skill_meta_provides(self):
        assert "arxiv_papers" in ArxivSkill.skill_meta.provides

    def test_skill_meta_consumes(self):
        assert "arxiv_query" in ArxivSkill.skill_meta.consumes

    def test_skill_meta_tags(self):
        assert "search" in ArxivSkill.skill_meta.tags
        assert "papers" in ArxivSkill.skill_meta.tags

    def test_skill_meta_requires(self):
        assert any("arxiv" in r for r in ArxivSkill.skill_meta.requires)

    def test_instantiation(self, skill: ArxivSkill):
        assert skill is not None
        assert skill.is_initialized


# ---------------------------------------------------------------------------
# _get_sort_criterion helper
# ---------------------------------------------------------------------------


class TestGetSortCriterion:
    def test_submitted_date(self):
        import arxiv

        criterion = _get_sort_criterion("submittedDate")
        assert criterion == arxiv.SortCriterion.SubmittedDate

    def test_relevance(self):
        import arxiv

        criterion = _get_sort_criterion("relevance")
        assert criterion == arxiv.SortCriterion.Relevance

    def test_last_updated_date(self):
        import arxiv

        criterion = _get_sort_criterion("lastUpdatedDate")
        assert criterion == arxiv.SortCriterion.LastUpdatedDate

    def test_unknown_falls_back_to_submitted_date(self):
        import arxiv

        criterion = _get_sort_criterion("bogus-value")
        assert criterion == arxiv.SortCriterion.SubmittedDate


# ---------------------------------------------------------------------------
# _result_to_dict
# ---------------------------------------------------------------------------


class TestResultToDict:
    def test_all_keys_present(self, fake_result: MagicMock):
        d = ArxivSkill._result_to_dict(fake_result)
        expected_keys = {
            "id", "title", "abstract", "authors", "categories",
            "published", "updated", "pdf_url", "arxiv_url",
        }
        assert expected_keys == set(d.keys())

    def test_values_correct(self, fake_result: MagicMock):
        d = ArxivSkill._result_to_dict(fake_result)
        assert d["id"] == fake_result.entry_id
        assert d["title"] == fake_result.title
        assert d["abstract"] == fake_result.summary
        assert d["pdf_url"] == fake_result.pdf_url
        assert d["arxiv_url"] == fake_result.entry_id

    def test_authors_are_strings(self, fake_result: MagicMock):
        d = ArxivSkill._result_to_dict(fake_result)
        assert all(isinstance(a, str) for a in d["authors"])

    def test_categories_are_list(self, fake_result: MagicMock):
        d = ArxivSkill._result_to_dict(fake_result)
        assert isinstance(d["categories"], list)

    def test_published_is_iso_string(self, fake_result: MagicMock):
        d = ArxivSkill._result_to_dict(fake_result)
        assert "2024-01-15" in d["published"]

    def test_updated_is_iso_string(self, fake_result: MagicMock):
        d = ArxivSkill._result_to_dict(fake_result)
        assert "2024-01-20" in d["updated"]

    def test_none_published_handled(self):
        result = _make_arxiv_result(published=None)
        result.published = None
        d = ArxivSkill._result_to_dict(result)
        assert d["published"] is None

    def test_none_updated_handled(self):
        result = _make_arxiv_result()
        result.updated = None
        d = ArxivSkill._result_to_dict(result)
        assert d["updated"] is None


# ---------------------------------------------------------------------------
# _build_search
# ---------------------------------------------------------------------------


class TestBuildSearch:
    def test_default_config(self, skill: ArxivSkill):
        import arxiv

        with patch("arxiv.Search") as MockSearch:
            MockSearch.return_value = MagicMock()
            skill._build_search("transformers")
            args, kwargs = MockSearch.call_args
            assert kwargs.get("query") == "transformers" or args[0] == "transformers"
            assert kwargs.get("max_results") == 20

    def test_custom_max_results(self):
        skill = _make_skill({"max_results": 5})
        import arxiv

        with patch("arxiv.Search") as MockSearch:
            MockSearch.return_value = MagicMock()
            skill._build_search("diffusion")
            _, kwargs = MockSearch.call_args
            assert kwargs.get("max_results") == 5

    def test_categories_appended_to_query(self):
        skill = _make_skill({"categories": ["math.CO", "math.NT"]})
        import arxiv

        with patch("arxiv.Search") as MockSearch:
            MockSearch.return_value = MagicMock()
            skill._build_search("primes")
            _, kwargs = MockSearch.call_args
            query = kwargs.get("query", "")
            assert "cat:math.CO" in query
            assert "cat:math.NT" in query
            assert "primes" in query

    def test_empty_query_with_categories(self):
        skill = _make_skill({"categories": ["cs.AI"]})
        import arxiv

        with patch("arxiv.Search") as MockSearch:
            MockSearch.return_value = MagicMock()
            skill._build_search("")
            _, kwargs = MockSearch.call_args
            query = kwargs.get("query", "")
            assert "cat:cs.AI" in query

    def test_no_categories_query_unchanged(self, skill: ArxivSkill):
        import arxiv

        with patch("arxiv.Search") as MockSearch:
            MockSearch.return_value = MagicMock()
            skill._build_search("neural networks")
            _, kwargs = MockSearch.call_args
            assert kwargs.get("query") == "neural networks"


# ---------------------------------------------------------------------------
# process() — core behaviour
# ---------------------------------------------------------------------------


def _patch_client_results(results: list[Any]):
    """Return a context manager that patches ``arxiv.Client.results``."""
    return patch(
        "arxiv.Client.results",
        return_value=iter(results),
    )


class TestProcess:
    def test_empty_query_sets_empty_list(self, skill: ArxivSkill):
        ctx = FlowContext()
        ctx.set("arxiv_query", "")

        result_ctx = asyncio.run(skill.process(ctx))
        assert result_ctx.get("arxiv_papers") == []

    def test_no_query_key_sets_empty_list(self, skill: ArxivSkill):
        ctx = FlowContext()
        # arxiv_query is absent

        result_ctx = asyncio.run(skill.process(ctx))
        assert result_ctx.get("arxiv_papers") == []

    def test_returns_flow_context(self, skill: ArxivSkill, fake_result: MagicMock):
        ctx = FlowContext()
        ctx.set("arxiv_query", "transformers")

        with _patch_client_results([fake_result]):
            result_ctx = asyncio.run(skill.process(ctx))
        assert isinstance(result_ctx, FlowContext)

    def test_single_result_returned(self, skill: ArxivSkill, fake_result: MagicMock):
        ctx = FlowContext()
        ctx.set("arxiv_query", "attention is all you need")

        with _patch_client_results([fake_result]):
            result_ctx = asyncio.run(skill.process(ctx))

        papers = result_ctx.get("arxiv_papers")
        assert isinstance(papers, list)
        assert len(papers) == 1

    def test_multiple_results_returned(self, skill: ArxivSkill):
        results = [_make_arxiv_result(entry_id=f"https://arxiv.org/abs/2401.{i:05d}") for i in range(3)]
        ctx = FlowContext()
        ctx.set("arxiv_query", "deep learning")

        with _patch_client_results(results):
            result_ctx = asyncio.run(skill.process(ctx))

        papers = result_ctx.get("arxiv_papers")
        assert len(papers) == 3

    def test_paper_dict_has_required_keys(self, skill: ArxivSkill, fake_result: MagicMock):
        ctx = FlowContext()
        ctx.set("arxiv_query", "gpt-4")

        with _patch_client_results([fake_result]):
            result_ctx = asyncio.run(skill.process(ctx))

        paper = result_ctx.get("arxiv_papers")[0]
        for key in ("id", "title", "abstract", "authors", "categories",
                    "published", "updated", "pdf_url", "arxiv_url"):
            assert key in paper, f"Missing key: {key}"

    def test_does_not_raise_on_api_failure(self, skill: ArxivSkill):
        ctx = FlowContext()
        ctx.set("arxiv_query", "quantum computing")

        with patch("arxiv.Client.results", side_effect=RuntimeError("network error")):
            result_ctx = asyncio.run(skill.process(ctx))

        # Must not raise; papers set to empty list
        papers = result_ctx.get("arxiv_papers")
        assert papers == []

    def test_api_failure_logs_error(self, skill: ArxivSkill):
        ctx = FlowContext()
        ctx.set("arxiv_query", "topology")

        with patch("arxiv.Client.results", side_effect=ConnectionError("timeout")):
            with patch("neurocore_skill_arxiv.skill.logger") as mock_logger:
                mock_logger.bind.return_value = mock_logger
                asyncio.run(skill.process(ctx))
                mock_logger.error.assert_called_once()

    def test_context_key_preserved_after_process(self, skill: ArxivSkill, fake_result: MagicMock):
        """Other context keys must survive the process call unchanged."""
        ctx = FlowContext()
        ctx.set("arxiv_query", "geometry")
        ctx.set("user_id", "u-999")

        with _patch_client_results([fake_result]):
            result_ctx = asyncio.run(skill.process(ctx))

        assert result_ctx.get("user_id") == "u-999"

    def test_download_pdfs_false_does_not_download(self, skill: ArxivSkill, fake_result: MagicMock):
        """When download_pdfs=False (default), no PDF download should occur."""
        ctx = FlowContext()
        ctx.set("arxiv_query", "manifolds")

        with _patch_client_results([fake_result]):
            with patch.object(skill, "_download_all_pdfs", new_callable=AsyncMock) as mock_dl:
                asyncio.run(skill.process(ctx))
                mock_dl.assert_not_called()

    def test_download_pdfs_true_triggers_download(self, fake_result: MagicMock):
        """When download_pdfs=True, _download_all_pdfs should be called."""
        skill = _make_skill({"download_pdfs": True, "pdf_dir": "/tmp/test_pdfs"})
        ctx = FlowContext()
        ctx.set("arxiv_query", "algebraic geometry")

        with _patch_client_results([fake_result]):
            with patch.object(skill, "_download_all_pdfs", new_callable=AsyncMock) as mock_dl:
                asyncio.run(skill.process(ctx))
                mock_dl.assert_called_once()


# ---------------------------------------------------------------------------
# PDF download behaviour
# ---------------------------------------------------------------------------


class TestDownloadAllPdfs:
    def test_creates_pdf_dir(self, skill: ArxivSkill, fake_result: MagicMock, tmp_path: Path):
        skill = _make_skill({"download_pdfs": True, "pdf_dir": str(tmp_path / "new_dir")})

        # Patch the ID-based re-fetch to return our fake result
        with patch("arxiv.Client.results", return_value=iter([fake_result])):
            # download_pdf on the fake result is already a MagicMock — let it be a no-op
            asyncio.run(
                skill._download_all_pdfs([ArxivSkill._result_to_dict(fake_result)], MagicMock())
            )
        assert (tmp_path / "new_dir").exists()

    def test_pdf_download_error_does_not_propagate(
        self, skill: ArxivSkill, fake_result: MagicMock, tmp_path: Path
    ):
        """A per-PDF download failure must be swallowed, not re-raised."""
        skill = _make_skill({"download_pdfs": True, "pdf_dir": str(tmp_path)})
        fake_result.download_pdf.side_effect = OSError("disk full")

        with patch("arxiv.Client.results", return_value=iter([fake_result])):
            # Should complete without raising
            asyncio.run(
                skill._download_all_pdfs([ArxivSkill._result_to_dict(fake_result)], MagicMock())
            )

    def test_id_refetch_failure_does_not_propagate(
        self, skill: ArxivSkill, tmp_path: Path
    ):
        """If the ID-based re-fetch itself fails, the method must not raise."""
        skill = _make_skill({"download_pdfs": True, "pdf_dir": str(tmp_path)})
        paper = {"id": "https://arxiv.org/abs/2401.00001", "title": "X"}

        with patch("arxiv.Client.results", side_effect=RuntimeError("network")):
            asyncio.run(skill._download_all_pdfs([paper], MagicMock()))


# ---------------------------------------------------------------------------
# Config validation via skill_meta.config_schema
# ---------------------------------------------------------------------------


class TestConfigValidation:
    def test_valid_config_no_errors(self):
        skill = _make_skill(
            {
                "max_results": 10,
                "sort_by": "relevance",
                "download_pdfs": False,
                "pdf_dir": "./out",
            }
        )
        errors = skill.validate_config()
        assert errors == []

    def test_wrong_type_for_max_results(self):
        skill = _make_skill({"max_results": "ten"})
        errors = skill.validate_config()
        assert any("max_results" in e for e in errors)

    def test_wrong_type_for_download_pdfs(self):
        skill = _make_skill({"download_pdfs": "yes"})
        errors = skill.validate_config()
        assert any("download_pdfs" in e for e in errors)

    def test_empty_config_no_errors(self):
        skill = _make_skill({})
        errors = skill.validate_config()
        assert errors == []


# ---------------------------------------------------------------------------
# Import / entry-point smoke test
# ---------------------------------------------------------------------------


class TestImports:
    def test_import_from_package(self):
        from neurocore_skill_arxiv import ArxivSkill as imported

        assert imported is ArxivSkill

    def test_arxiv_skill_is_async_skill(self):
        from neurocore import AsyncSkill as Base

        assert issubclass(ArxivSkill, Base)
