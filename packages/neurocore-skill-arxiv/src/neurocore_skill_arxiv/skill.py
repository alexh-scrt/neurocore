"""ArxivSkill — search arXiv preprints and optionally download PDFs.

This skill wraps the synchronous ``arxiv`` library in an async interface by
running the blocking network calls in the default thread-pool executor.  PDF
downloads are performed concurrently with ``asyncio.gather``.

Context contract
----------------
Consumes:
    arxiv_query (str): Free-text search query forwarded to the arXiv API.

Provides:
    arxiv_papers (list[dict]): One dict per result with keys:
        id, title, abstract, authors, categories, published, updated,
        pdf_url, arxiv_url.

Config keys (all optional)
---------------------------
max_results   int   20      Maximum number of results to return.
sort_by       str   "submittedDate"
                            Sort order: ``submittedDate`` | ``relevance`` |
                            ``lastUpdatedDate``.
categories    list  []      If non-empty, restrict to these arXiv category
                            codes, e.g. ``["math.CO", "cs.LG"]``.
download_pdfs bool  False   When True, download every PDF to ``pdf_dir``.
pdf_dir       str   "./papers"
                            Directory into which PDFs are saved.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import structlog

from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Sort-criterion mapping
# ---------------------------------------------------------------------------

_SORT_MAP: dict[str, Any] = {}  # populated lazily to avoid import-time cost


def _get_sort_criterion(sort_by: str) -> Any:
    """Convert a string sort key to an ``arxiv.SortCriterion`` enum value.

    Falls back to ``SortCriterion.SubmittedDate`` for unknown strings so that
    invalid config does not crash the skill.
    """
    import arxiv  # noqa: PLC0415 — deferred to avoid hard import at module level

    if not _SORT_MAP:
        _SORT_MAP.update(
            {
                "submittedDate": arxiv.SortCriterion.SubmittedDate,
                "relevance": arxiv.SortCriterion.Relevance,
                "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
            }
        )
    return _SORT_MAP.get(sort_by, arxiv.SortCriterion.SubmittedDate)


# ---------------------------------------------------------------------------
# Main skill
# ---------------------------------------------------------------------------


class ArxivSkill(AsyncSkill):
    """Async skill that searches arXiv and optionally downloads PDFs.

    Registered under the entry-point key ``arxiv`` so that blueprints can
    reference it as ``type: arxiv``.
    """

    skill_meta = SkillMeta(
        name="arxiv",
        version="0.1.1",
        description="Search arXiv preprints and download PDFs",
        provides=["arxiv_papers"],
        consumes=["arxiv_query"],
        config_schema={
            "properties": {
                "max_results": {"type": "integer", "default": 20},
                "sort_by": {
                    "type": "string",
                    "default": "submittedDate",
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "download_pdfs": {"type": "boolean", "default": False},
                "pdf_dir": {"type": "string", "default": "./papers"},
            }
        },
        requires=["arxiv>=2.1.0"],
        tags=["search", "papers", "preprints"],
        max_retries=3,
        retry_delay_base=2.0,
        retry_delay_max=30.0,
    )

    # ------------------------------------------------------------------
    # Helpers — pure functions extracted for testability
    # ------------------------------------------------------------------

    def _build_search(self, query: str) -> Any:
        """Construct an ``arxiv.Search`` object from current config.

        Separated from ``process`` so that tests can patch it or call it
        directly without invoking the network.

        Args:
            query: The free-text search string.

        Returns:
            An ``arxiv.Search`` instance ready to be iterated.
        """
        import arxiv  # noqa: PLC0415

        max_results: int = int(self.config.get("max_results", 20))
        sort_by: str = str(self.config.get("sort_by", "submittedDate"))
        categories: list[str] = list(self.config.get("categories") or [])

        if categories:
            # Combine caller's query with category restriction using arXiv
            # query syntax.  Example: "(attention) AND (cat:cs.LG OR cat:cs.AI)"
            cat_clause = " OR ".join(f"cat:{c}" for c in categories)
            full_query = f"({query}) AND ({cat_clause})" if query else cat_clause
        else:
            full_query = query

        return arxiv.Search(
            query=full_query,
            max_results=max_results,
            sort_by=_get_sort_criterion(sort_by),
        )

    @staticmethod
    def _result_to_dict(result: Any) -> dict[str, Any]:
        """Serialise a single ``arxiv.Result`` into a plain Python dict.

        Args:
            result: An ``arxiv.Result`` instance.

        Returns:
            A dict with the keys required by the behaviour contract.
        """
        return {
            "id": result.entry_id,
            "title": result.title,
            "abstract": result.summary,
            "authors": [str(a) for a in result.authors],
            "categories": list(result.categories),
            "published": result.published.isoformat() if result.published else None,
            "updated": result.updated.isoformat() if result.updated else None,
            "pdf_url": result.pdf_url,
            "arxiv_url": result.entry_id,
        }

    # ------------------------------------------------------------------
    # Async download helpers
    # ------------------------------------------------------------------

    async def _download_pdf(
        self,
        result: Any,
        pdf_dir: Path,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Download a single PDF in the thread-pool executor.

        Errors are caught and logged; they do not propagate so that a single
        failed download does not abort the rest.

        Args:
            result: ``arxiv.Result`` whose PDF should be downloaded.
            pdf_dir: Directory into which the file is saved.
            loop:    The running event loop used to schedule the executor call.
        """
        paper_id = result.entry_id.rstrip("/").split("/")[-1]
        dest = pdf_dir / f"{paper_id}.pdf"

        try:
            await loop.run_in_executor(
                None,
                lambda: result.download_pdf(dirpath=str(pdf_dir), filename=f"{paper_id}.pdf"),
            )
            logger.debug("arxiv.pdf_downloaded", paper_id=paper_id, dest=str(dest))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "arxiv.pdf_download_failed",
                paper_id=paper_id,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def process(self, context: FlowContext) -> FlowContext:  # type: ignore[override]
        """Execute the arXiv search and optionally download PDFs.

        Reads ``arxiv_query`` from *context*, performs the search, and writes
        the list of paper dicts back as ``arxiv_papers``.  All blocking arXiv
        library calls run in the default thread-pool executor so they do not
        block the event loop.

        On any failure the skill sets ``arxiv_papers`` to an empty list and
        logs the error at ERROR level — it never raises.

        Args:
            context: The shared ``FlowContext`` from the running blueprint.

        Returns:
            The same *context* object with ``arxiv_papers`` set.
        """
        query: str = context.get("arxiv_query") or ""
        log = logger.bind(skill="arxiv", query=query)

        if not query:
            log.warning("arxiv.empty_query")
            context.set("arxiv_papers", [])
            return context

        try:
            papers = await self._fetch_papers(query, log)
        except Exception as exc:  # noqa: BLE001
            log.error("arxiv.search_failed", error=str(exc))
            context.set("arxiv_papers", [])
            return context

        context.set("arxiv_papers", papers)
        log.info("arxiv.search_complete", result_count=len(papers))

        # Optionally download PDFs
        download_pdfs: bool = bool(self.config.get("download_pdfs", False))
        if download_pdfs and papers:
            await self._download_all_pdfs(papers, log)

        return context

    async def _fetch_papers(
        self, query: str, log: Any
    ) -> list[dict[str, Any]]:
        """Run the blocking arXiv search in the thread-pool executor.

        Args:
            query: Free-text search string.
            log:   Bound structlog logger for contextual logging.

        Returns:
            List of paper dicts.

        Raises:
            Exception: Propagates any exception raised by the arXiv client so
                       that ``process`` can catch it and set an empty result.
        """
        import arxiv  # noqa: PLC0415

        loop = asyncio.get_event_loop()
        search = self._build_search(query)
        client = arxiv.Client()

        log.debug("arxiv.search_start", max_results=self.config.get("max_results", 20))

        def _run_search() -> list[Any]:
            return list(client.results(search))

        raw_results: list[Any] = await loop.run_in_executor(None, _run_search)
        return [self._result_to_dict(r) for r in raw_results]

    async def _download_all_pdfs(
        self, papers: list[dict[str, Any]], log: Any
    ) -> None:
        """Concurrently download PDFs for all papers in *papers*.

        The paper dicts do not carry ``arxiv.Result`` objects, so we re-issue a
        targeted search (by ID) for each paper to obtain the result object
        needed by ``result.download_pdf``.  Downloads run concurrently via
        ``asyncio.gather``.

        Args:
            papers: List of paper dicts produced by ``_fetch_papers``.
            log:    Bound structlog logger.
        """
        import arxiv  # noqa: PLC0415

        pdf_dir = Path(str(self.config.get("pdf_dir", "./papers")))
        pdf_dir.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_event_loop()
        client = arxiv.Client()

        # Re-fetch result objects by ID so we can call download_pdf on them.
        paper_ids = [p["id"].rstrip("/").split("/abs/")[-1] for p in papers]

        def _fetch_by_ids() -> list[Any]:
            id_search = arxiv.Search(id_list=paper_ids)
            return list(client.results(id_search))

        try:
            result_objects: list[Any] = await loop.run_in_executor(None, _fetch_by_ids)
        except Exception as exc:  # noqa: BLE001
            log.error("arxiv.id_refetch_failed", error=str(exc))
            return

        log.debug("arxiv.pdf_downloads_start", count=len(result_objects))
        await asyncio.gather(
            *[self._download_pdf(r, pdf_dir, loop) for r in result_objects],
            return_exceptions=True,
        )
        log.info("arxiv.pdf_downloads_complete", pdf_dir=str(pdf_dir))
