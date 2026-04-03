"""TavilySkill — web search, URL extraction, and deep research via Tavily API.

Modes
-----
search
    Run a standard or deep web search using ``TavilyClient.search()``.
    Reads ``tavily_query`` from context and writes results to ``tavily_results``.

extract
    Extract structured content from specific URLs using ``TavilyClient.extract()``.
    Reads ``tavily_urls`` from context and writes results to ``tavily_results``.

research
    Perform asynchronous deep research (calls search iteratively or via
    ``TavilyClient.qna_search`` if available) and writes consolidated results
    to ``tavily_results``.

Configuration
-------------
api_key : str, required
    Tavily API key. Can be set via the ``TAVILY_API_KEY`` environment variable.
mode : str, default "search"
    One of ``search``, ``extract``, ``research``.
max_results : int, default 5
    Maximum number of results to return (search / research modes).
search_depth : str, default "basic"
    Either ``"basic"`` or ``"advanced"``.
include_domains : list[str], default []
    Restrict results to these domains.
exclude_domains : list[str], default []
    Exclude results from these domains.
topic : str, default "general"
    Topic hint: ``"general"`` or ``"news"``.
urls : list[str], default []
    URLs to extract content from (extract mode). Can also be supplied at
    runtime via the ``tavily_urls`` context key.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from flowengine import FlowContext

from neurocore import AsyncSkill, SkillMeta

logger = logging.getLogger(__name__)

_VALID_MODES = {"search", "extract", "research"}
_VALID_DEPTHS = {"basic", "advanced"}
_VALID_TOPICS = {"general", "news"}


class TavilySkill(AsyncSkill):
    """Async skill that integrates Tavily web search, extraction, and research."""

    skill_meta = SkillMeta(
        name="tavily",
        version="0.1.0",
        description="Web search, URL extraction, and deep research via the Tavily API",
        author="NeuroCore Contributors",
        requires=["tavily-python>=0.5"],
        provides=["tavily_results"],
        consumes=["tavily_query", "tavily_urls"],
        tags=["search", "web", "research", "extract"],
        config_schema={
            "required": ["api_key"],
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "Tavily API key",
                },
                "mode": {
                    "type": "string",
                    "description": "Operation mode: search | extract | research",
                    "enum": ["search", "extract", "research"],
                    "default": "search",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 5,
                },
                "search_depth": {
                    "type": "string",
                    "description": "Search depth: basic | advanced",
                    "enum": ["basic", "advanced"],
                    "default": "basic",
                },
                "include_domains": {
                    "type": "array",
                    "description": "Restrict results to these domains",
                    "items": {"type": "string"},
                    "default": [],
                },
                "exclude_domains": {
                    "type": "array",
                    "description": "Exclude results from these domains",
                    "items": {"type": "string"},
                    "default": [],
                },
                "topic": {
                    "type": "string",
                    "description": "Topic hint: general | news",
                    "enum": ["general", "news"],
                    "default": "general",
                },
                "urls": {
                    "type": "array",
                    "description": "URLs for extract mode (overridden by tavily_urls context key)",
                    "items": {"type": "string"},
                    "default": [],
                },
            },
        },
    )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_api_key(self) -> str:
        """Return the API key from config or environment."""
        return self.config.get("api_key", "") or os.environ.get("TAVILY_API_KEY", "")

    def _build_client(self) -> Any:
        """Instantiate and return a TavilyClient."""
        from tavily import TavilyClient  # type: ignore[import-untyped]

        api_key = self._resolve_api_key()
        return TavilyClient(api_key=api_key)

    # ------------------------------------------------------------------
    # Mode implementations
    # ------------------------------------------------------------------

    async def _run_search(self, client: Any, query: str) -> list[dict[str, Any]]:
        """Execute a standard web search and return result items."""
        max_results: int = int(self.config.get("max_results", 5))
        search_depth: str = str(self.config.get("search_depth", "basic"))
        include_domains: list[str] = list(self.config.get("include_domains", []))
        exclude_domains: list[str] = list(self.config.get("exclude_domains", []))
        topic: str = str(self.config.get("topic", "general"))

        kwargs: dict[str, Any] = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "topic": topic,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains

        response = client.search(**kwargs)
        return response.get("results", [])  # type: ignore[return-value]

    async def _run_extract(self, client: Any, urls: list[str]) -> list[dict[str, Any]]:
        """Extract structured content from a list of URLs."""
        response = client.extract(urls=urls)
        # extract returns {"results": [...], "failed_results": [...]}
        return response.get("results", [])  # type: ignore[return-value]

    async def _run_research(self, client: Any, query: str) -> list[dict[str, Any]]:
        """Deep research: perform multiple searches and aggregate results."""
        max_results: int = int(self.config.get("max_results", 5))
        include_domains: list[str] = list(self.config.get("include_domains", []))
        exclude_domains: list[str] = list(self.config.get("exclude_domains", []))

        # Attempt to use qna_search for a concise researched answer first,
        # then supplement with a deep search pass.
        aggregated: list[dict[str, Any]] = []

        # Pass 1: advanced search
        kwargs: dict[str, Any] = {
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
            "topic": str(self.config.get("topic", "general")),
        }
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains

        response = client.search(**kwargs)
        aggregated.extend(response.get("results", []))

        # Pass 2: if TavilyClient exposes qna_search, call it and attach answer
        if hasattr(client, "qna_search"):
            try:
                answer: str = client.qna_search(query=query)
                aggregated.insert(
                    0,
                    {
                        "type": "answer",
                        "content": answer,
                        "url": "",
                        "title": "Research Answer",
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("qna_search failed (non-fatal): %s", exc)

        return aggregated

    # ------------------------------------------------------------------
    # AsyncSkill interface
    # ------------------------------------------------------------------

    async def process(self, context: FlowContext) -> FlowContext:
        """Execute the configured Tavily operation and write results to context.

        Reads:
            tavily_query (str): The search or research query.
            tavily_urls (list[str]): URLs for extract mode (optional override).

        Writes:
            tavily_results (list[dict]): List of result items from Tavily.
                Set to ``[]`` on any failure.
        """
        mode: str = str(self.config.get("mode", "search"))

        if mode not in _VALID_MODES:
            logger.error(
                "TavilySkill: invalid mode %r — must be one of %s. Setting empty results.",
                mode,
                sorted(_VALID_MODES),
            )
            context.set("tavily_results", [])
            return context

        try:
            client = self._build_client()
        except Exception as exc:  # noqa: BLE001
            logger.error("TavilySkill: failed to build TavilyClient: %s", exc)
            context.set("tavily_results", [])
            return context

        results: list[dict[str, Any]] = []

        try:
            if mode == "search":
                query: str = str(context.get("tavily_query", ""))
                if not query:
                    logger.warning("TavilySkill: 'tavily_query' is empty; returning no results.")
                else:
                    results = await self._run_search(client, query)

            elif mode == "extract":
                # Context key takes priority over config-level urls
                urls: list[str] = list(context.get("tavily_urls") or self.config.get("urls", []))
                if not urls:
                    logger.warning(
                        "TavilySkill: 'tavily_urls' is empty for extract mode; "
                        "returning no results."
                    )
                else:
                    results = await self._run_extract(client, urls)

            elif mode == "research":
                query = str(context.get("tavily_query", ""))
                if not query:
                    logger.warning(
                        "TavilySkill: 'tavily_query' is empty for research mode; "
                        "returning no results."
                    )
                else:
                    results = await self._run_research(client, query)

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "TavilySkill: error during %s operation: %s", mode, exc, exc_info=True
            )
            results = []

        context.set("tavily_results", results)
        return context
