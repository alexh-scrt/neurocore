"""CoreApiSkill — open-access research works search via the CORE API v3.

Searches the CORE aggregation platform (https://core.ac.uk) for open-access
academic works matching a free-text query.

Configuration
-------------
api_key : str, required
    CORE API key. Can be set via the ``CORE_API_KEY`` environment variable.
limit : int, default 10
    Maximum number of works to return per request.
fulltext : bool, default False
    If True, attempt to include full-text content where available.

Context keys
------------
Reads:
    core_query (str): Free-text search query.

Writes:
    core_works (list[dict]): List of work items from CORE.
        Set to ``[]`` on any failure.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from flowengine import FlowContext

from neurocore import AsyncSkill, SkillMeta

logger = logging.getLogger(__name__)

_CORE_SEARCH_URL = "https://api.core.ac.uk/v3/search/works"
_DEFAULT_LIMIT = 10
_REQUEST_TIMEOUT = 30.0  # seconds


class CoreApiSkill(AsyncSkill):
    """Async skill that queries the CORE open-access research API."""

    skill_meta = SkillMeta(
        name="core-api",
        version="0.1.1",
        description="Search open-access research works via the CORE API v3",
        author="NeuroCore Contributors",
        requires=["httpx>=0.27"],
        provides=["core_works"],
        consumes=["core_query"],
        tags=["research", "academic", "open-access", "core"],
        max_retries=3,
        retry_delay_base=2.0,
        retry_delay_max=30.0,
        config_schema={
            "required": ["api_key"],
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "CORE API key",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of works to return",
                    "default": 10,
                },
                "fulltext": {
                    "type": "boolean",
                    "description": "Request full-text content where available",
                    "default": False,
                },
            },
        },
    )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_api_key(self) -> str:
        """Return the API key from config or environment."""
        return self.config.get("api_key", "") or os.environ.get("CORE_API_KEY", "")

    def _build_request_params(self, query: str) -> dict[str, Any]:
        """Build the query-string parameters for the CORE search endpoint."""
        limit: int = int(self.config.get("limit", _DEFAULT_LIMIT))
        fulltext: bool = bool(self.config.get("fulltext", False))

        params: dict[str, Any] = {
            "q": query,
            "limit": limit,
        }
        if fulltext:
            params["fulltext"] = "true"
        return params

    def _serialize_works(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and normalise work items from a CORE API response."""
        raw_results: list[dict[str, Any]] = data.get("results", [])
        works: list[dict[str, Any]] = []
        for item in raw_results:
            work: dict[str, Any] = {
                "id": item.get("id"),
                "title": item.get("title", ""),
                "abstract": item.get("abstract", ""),
                "year": item.get("yearPublished"),
                "authors": [
                    a.get("name", "") for a in item.get("authors", []) if isinstance(a, dict)
                ],
                "doi": item.get("doi"),
                "download_url": item.get("downloadUrl"),
                "source_fulltext_urls": item.get("sourceFulltextUrls", []),
                "publisher": item.get("publisher"),
                "language": item.get("language", {}).get("name") if item.get("language") else None,
            }
            # Include full-text if present in response
            if "fullText" in item:
                work["full_text"] = item["fullText"]
            works.append(work)
        return works

    # ------------------------------------------------------------------
    # AsyncSkill interface
    # ------------------------------------------------------------------

    async def process(self, context: FlowContext) -> FlowContext:
        """Search CORE for research works and write results to context.

        Reads:
            core_query (str): Free-text search query.

        Writes:
            core_works (list[dict]): Normalised list of work items.
                Set to ``[]`` on any failure.
        """
        query: str = str(context.get("core_query", ""))

        if not query:
            logger.warning("CoreApiSkill: 'core_query' is empty; returning no results.")
            context.set("core_works", [])
            return context

        api_key = self._resolve_api_key()
        if not api_key:
            logger.error(
                "CoreApiSkill: no API key provided — set 'api_key' in config "
                "or the CORE_API_KEY environment variable."
            )
            context.set("core_works", [])
            return context

        params = self._build_request_params(query)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }

        works: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                response = await client.get(
                    _CORE_SEARCH_URL,
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                works = self._serialize_works(data)

        except httpx.HTTPStatusError as exc:
            logger.error(
                "CoreApiSkill: HTTP %s error from CORE API: %s",
                exc.response.status_code,
                exc,
            )
        except httpx.RequestError as exc:
            logger.error("CoreApiSkill: request error contacting CORE API: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("CoreApiSkill: unexpected error: %s", exc, exc_info=True)

        context.set("core_works", works)
        return context
