"""ExaSkill — neural search and find-similar via the Exa API.

Modes
-----
search
    Full neural / keyword search using ``Exa.search_and_contents()``.
    Reads ``exa_query`` from context and writes results to ``exa_results``.

find_similar
    Find URLs similar to a seed URL using ``Exa.find_similar_and_contents()``.
    Reads ``exa_query`` (treated as the seed URL) from context and writes
    results to ``exa_results``.

Configuration
-------------
api_key : str, required
    Exa API key. Can be set via the ``EXA_API_KEY`` environment variable.
mode : str, default "search"
    One of ``search``, ``find_similar``.
num_results : int, default 10
    Number of results to return.
category : str | None, default None
    Exa content category filter (e.g. ``"research paper"``, ``"news"``).
include_domains : list[str], default []
    Restrict results to these domains.
use_autoprompt : bool, default True
    Whether Exa should auto-enhance the query.
include_text : bool, default False
    Whether to include full page text in results.
similarity_url : str | None, default None
    Seed URL for find_similar mode. Overrides ``exa_query`` if provided.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from flowengine import FlowContext

from neurocore import AsyncSkill, SkillMeta

logger = logging.getLogger(__name__)

_VALID_MODES = {"search", "find_similar"}


class ExaSkill(AsyncSkill):
    """Async skill that integrates Exa neural search and find-similar."""

    skill_meta = SkillMeta(
        name="exa",
        version="0.1.1",
        description="Neural web search and find-similar via the Exa API",
        author="NeuroCore Contributors",
        requires=["exa-py>=1.1"],
        provides=["exa_results"],
        consumes=["exa_query"],
        tags=["search", "neural", "web", "exa"],
        max_retries=3,
        retry_delay_base=2.0,
        retry_delay_max=30.0,
        config_schema={
            "required": ["api_key"],
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "Exa API key",
                },
                "mode": {
                    "type": "string",
                    "description": "Operation mode: search | find_similar",
                    "enum": ["search", "find_similar"],
                    "default": "search",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 10,
                },
                "category": {
                    "type": "string",
                    "description": "Exa content category filter (e.g. 'research paper', 'news')",
                },
                "include_domains": {
                    "type": "array",
                    "description": "Restrict results to these domains",
                    "items": {"type": "string"},
                    "default": [],
                },
                "use_autoprompt": {
                    "type": "boolean",
                    "description": "Let Exa auto-enhance the query",
                    "default": True,
                },
                "include_text": {
                    "type": "boolean",
                    "description": "Include full page text in results",
                    "default": False,
                },
                "similarity_url": {
                    "type": "string",
                    "description": "Seed URL for find_similar mode",
                },
            },
        },
    )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_api_key(self) -> str:
        """Return the API key from config or environment."""
        return self.config.get("api_key", "") or os.environ.get("EXA_API_KEY", "")

    def _build_client(self) -> Any:
        """Instantiate and return an Exa client."""
        from exa_py import Exa  # type: ignore[import-untyped]

        api_key = self._resolve_api_key()
        return Exa(api_key=api_key)

    def _serialize_results(self, response: Any) -> list[dict[str, Any]]:
        """Convert an Exa SearchResponse to a plain list of dicts."""
        items: list[dict[str, Any]] = []
        results = getattr(response, "results", [])
        for r in results:
            item: dict[str, Any] = {
                "title": getattr(r, "title", ""),
                "url": getattr(r, "url", ""),
                "published_date": getattr(r, "published_date", None),
                "author": getattr(r, "author", None),
                "score": getattr(r, "score", None),
            }
            # include_text contents
            text = getattr(r, "text", None)
            if text is not None:
                item["text"] = text
            highlights = getattr(r, "highlights", None)
            if highlights is not None:
                item["highlights"] = highlights
            items.append(item)
        return items

    # ------------------------------------------------------------------
    # Mode implementations
    # ------------------------------------------------------------------

    async def _run_search(self, client: Any, query: str) -> list[dict[str, Any]]:
        """Execute a neural/keyword search."""
        num_results: int = int(self.config.get("num_results", 10))
        use_autoprompt: bool = bool(self.config.get("use_autoprompt", True))
        include_domains: list[str] = list(self.config.get("include_domains", []))
        include_text: bool = bool(self.config.get("include_text", False))
        category: str | None = self.config.get("category") or None

        search_kwargs: dict[str, Any] = {
            "query": query,
            "num_results": num_results,
            "use_autoprompt": use_autoprompt,
        }
        if include_domains:
            search_kwargs["include_domains"] = include_domains
        if category:
            search_kwargs["category"] = category
        if include_text:
            search_kwargs["text"] = True

        # Use search_and_contents to get rich result objects
        if hasattr(client, "search_and_contents"):
            response = client.search_and_contents(**search_kwargs)
        else:
            # Fallback to plain search
            response = client.search(**search_kwargs)

        return self._serialize_results(response)

    async def _run_find_similar(self, client: Any, url: str) -> list[dict[str, Any]]:
        """Find URLs similar to the provided seed URL."""
        num_results: int = int(self.config.get("num_results", 10))
        include_domains: list[str] = list(self.config.get("include_domains", []))
        include_text: bool = bool(self.config.get("include_text", False))

        kwargs: dict[str, Any] = {
            "url": url,
            "num_results": num_results,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains
        if include_text:
            kwargs["text"] = True

        if hasattr(client, "find_similar_and_contents"):
            response = client.find_similar_and_contents(**kwargs)
        else:
            response = client.find_similar(**kwargs)

        return self._serialize_results(response)

    # ------------------------------------------------------------------
    # AsyncSkill interface
    # ------------------------------------------------------------------

    async def process(self, context: FlowContext) -> FlowContext:
        """Execute the configured Exa operation and write results to context.

        Reads:
            exa_query (str): The search query or (for find_similar) seed URL.

        Writes:
            exa_results (list[dict]): List of result items from Exa.
                Set to ``[]`` on any failure.
        """
        mode: str = str(self.config.get("mode", "search"))

        if mode not in _VALID_MODES:
            logger.error(
                "ExaSkill: invalid mode %r — must be one of %s. Setting empty results.",
                mode,
                sorted(_VALID_MODES),
            )
            context.set("exa_results", [])
            return context

        try:
            client = self._build_client()
        except Exception as exc:  # noqa: BLE001
            logger.error("ExaSkill: failed to build Exa client: %s", exc)
            context.set("exa_results", [])
            return context

        results: list[dict[str, Any]] = []

        try:
            if mode == "search":
                query: str = str(context.get("exa_query", ""))
                if not query:
                    logger.warning("ExaSkill: 'exa_query' is empty; returning no results.")
                else:
                    results = await self._run_search(client, query)

            elif mode == "find_similar":
                # similarity_url config key takes priority, then exa_query
                url: str = str(
                    self.config.get("similarity_url") or context.get("exa_query", "")
                )
                if not url:
                    logger.warning(
                        "ExaSkill: no URL for find_similar mode — "
                        "set 'similarity_url' config or 'exa_query' context key."
                    )
                else:
                    results = await self._run_find_similar(client, url)

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "ExaSkill: error during %s operation: %s", mode, exc, exc_info=True
            )
            results = []

        context.set("exa_results", results)
        return context
