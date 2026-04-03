"""Semantic Scholar paper search skill for NeuroCore.

Supports three modes of paper retrieval:
- search: Full-text keyword search via the Semantic Scholar Graph API.
- recommendations: Paper recommendations based on positive paper IDs.
- citations: Retrieve papers that cite a specific paper by ID.

Context keys consumed:
    s2_query (str): The search query string (used by "search" mode).
    s2_positive_paper_ids (list[str]): Positive paper IDs for "recommendations" mode.

Context keys produced:
    s2_papers (list[dict]): List of paper dicts from the API response.

Configuration keys:
    mode (str): One of "search", "recommendations", "citations". Default: "search".
    api_key (str | None): Optional Semantic Scholar API key for higher rate limits.
    limit (int): Maximum number of results to return. Default: 10.
    fields (str): Comma-separated list of paper fields to request.
                  Default: "paperId,title,abstract,year,authors,url".
    paper_id (str | None): Paper ID required for "citations" mode.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from flowengine import FlowContext

from neurocore import AsyncSkill, SkillMeta

logger = logging.getLogger(__name__)

_BASE_GRAPH = "https://api.semanticscholar.org/graph/v1"
_BASE_RECOM = "https://api.semanticscholar.org/recommendations/v1"

_DEFAULT_FIELDS = "paperId,title,abstract,year,authors,url"
_DEFAULT_LIMIT = 10


class SemanticScholarSkill(AsyncSkill):
    """Fetch papers from the Semantic Scholar API.

    Supports search, recommendations, and citations modes. On any HTTP
    failure the skill sets ``s2_papers`` to an empty list and logs the
    error rather than raising an exception.

    Example blueprint config::

        skills:
          semantic-scholar:
            mode: search
            limit: 5
            fields: "paperId,title,year"
    """

    skill_meta = SkillMeta(
        name="semantic-scholar",
        version="0.1.0",
        description="Semantic Scholar paper search skill for NeuroCore",
        requires=["httpx>=0.27"],
        provides=["s2_papers"],
        consumes=["s2_query", "s2_positive_paper_ids"],
        tags=["research", "papers", "semantic-scholar", "academic"],
        config_schema={
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["search", "recommendations", "citations"],
                    "default": "search",
                },
                "api_key": {"type": "string"},
                "limit": {"type": "integer", "default": _DEFAULT_LIMIT},
                "fields": {"type": "string", "default": _DEFAULT_FIELDS},
                "paper_id": {"type": "string"},
            }
        },
    )

    async def process(self, context: FlowContext) -> FlowContext:
        """Fetch papers from Semantic Scholar and store results in context.

        Reads configuration from ``self.config`` and query data from
        ``context``. Always sets ``s2_papers`` in the context — on failure
        it is set to an empty list.

        Args:
            context: The active FlowContext.

        Returns:
            The updated FlowContext with ``s2_papers`` set.
        """
        mode: str = self.config.get("mode", "search")
        api_key: str | None = self.config.get("api_key")
        limit: int = int(self.config.get("limit", _DEFAULT_LIMIT))
        fields: str = self.config.get("fields", _DEFAULT_FIELDS)
        paper_id: str | None = self.config.get("paper_id")

        headers: dict[str, str] = {}
        if api_key:
            headers["x-api-key"] = api_key

        try:
            async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
                if mode == "search":
                    papers = await self._search(client, context, limit, fields)
                elif mode == "recommendations":
                    papers = await self._recommendations(client, context, limit, fields)
                elif mode == "citations":
                    papers = await self._citations(client, paper_id, limit, fields)
                else:
                    logger.error(
                        "SemanticScholarSkill: unknown mode %r; must be one of "
                        "'search', 'recommendations', 'citations'",
                        mode,
                    )
                    papers = []
        except httpx.HTTPError as exc:
            logger.error("SemanticScholarSkill: HTTP error during %r mode: %s", mode, exc)
            papers = []
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "SemanticScholarSkill: unexpected error during %r mode: %s", mode, exc
            )
            papers = []

        context.set("s2_papers", papers)
        return context

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _search(
        self,
        client: httpx.AsyncClient,
        context: FlowContext,
        limit: int,
        fields: str,
    ) -> list[dict[str, Any]]:
        """Execute a keyword search query.

        Args:
            client: Authenticated httpx async client.
            context: FlowContext providing ``s2_query``.
            limit: Maximum number of results.
            fields: Comma-separated paper fields to include.

        Returns:
            List of paper dicts, or empty list on failure.
        """
        query: str = context.get("s2_query", "")
        if not query:
            logger.warning("SemanticScholarSkill: 's2_query' is empty; returning no results")
            return []

        url = f"{_BASE_GRAPH}/paper/search"
        params: dict[str, Any] = {
            "query": query,
            "limit": limit,
            "fields": fields,
        }

        response = await client.get(url, params=params)
        if response.is_error:
            logger.error(
                "SemanticScholarSkill: search request failed with status %d: %s",
                response.status_code,
                response.text,
            )
            return []

        data = response.json()
        return data.get("data", [])

    async def _recommendations(
        self,
        client: httpx.AsyncClient,
        context: FlowContext,
        limit: int,
        fields: str,
    ) -> list[dict[str, Any]]:
        """Fetch paper recommendations based on positive paper IDs.

        Args:
            client: Authenticated httpx async client.
            context: FlowContext providing ``s2_positive_paper_ids``.
            limit: Maximum number of results.
            fields: Comma-separated paper fields to include.

        Returns:
            List of paper dicts, or empty list on failure.
        """
        positive_ids: list[str] = context.get("s2_positive_paper_ids", [])
        if not positive_ids:
            logger.warning(
                "SemanticScholarSkill: 's2_positive_paper_ids' is empty; "
                "returning no results"
            )
            return []

        url = f"{_BASE_RECOM}/papers"
        params: dict[str, Any] = {
            "limit": limit,
            "fields": fields,
        }
        payload: dict[str, Any] = {
            "positivePaperIds": positive_ids,
            "negativePaperIds": [],
        }

        response = await client.post(url, params=params, json=payload)
        if response.is_error:
            logger.error(
                "SemanticScholarSkill: recommendations request failed with status %d: %s",
                response.status_code,
                response.text,
            )
            return []

        data = response.json()
        return data.get("recommendedPapers", [])

    async def _citations(
        self,
        client: httpx.AsyncClient,
        paper_id: str | None,
        limit: int,
        fields: str,
    ) -> list[dict[str, Any]]:
        """Fetch papers that cite a specific paper.

        Args:
            client: Authenticated httpx async client.
            paper_id: The Semantic Scholar paper ID to look up citations for.
            limit: Maximum number of results.
            fields: Comma-separated paper fields to include.

        Returns:
            List of citing paper dicts, or empty list on failure.
        """
        if not paper_id:
            logger.error(
                "SemanticScholarSkill: 'paper_id' config is required for citations mode"
            )
            return []

        url = f"{_BASE_GRAPH}/paper/{paper_id}/citations"
        params: dict[str, Any] = {
            "limit": limit,
            "fields": fields,
        }

        response = await client.get(url, params=params)
        if response.is_error:
            logger.error(
                "SemanticScholarSkill: citations request failed with status %d: %s",
                response.status_code,
                response.text,
            )
            return []

        data = response.json()
        # Each entry in citations has a "citingPaper" key with the paper dict
        raw: list[dict[str, Any]] = data.get("data", [])
        return [entry.get("citingPaper", entry) for entry in raw]
