"""NeuroCore skill for querying the On-Line Encyclopedia of Integer Sequences.

Reads a search query string from the flow context, issues an HTTP GET to the
OEIS JSON search endpoint, and writes the list of matching sequence records to
``oeis_results``.

The skill never raises; on network or parse errors the result will be an empty
list.

Configuration keys (set via ``skill.init(config)``)::

    max_results     (int, default 10)  – maximum number of sequences to return
    timeout_seconds (int, default 15)  – HTTP request timeout in seconds

Context keys consumed:

    oeis_query – str  (search query, e.g. ``"1,1,2,3,5,8"`` or ``"fibonacci"``)

Context keys provided:

    oeis_results – list[dict]
        Each element is the raw JSON object for one OEIS sequence result,
        typically containing fields such as ``number``, ``name``, ``data``,
        ``offset``, ``comment``, ``formula``, ``link``, etc.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

__all__ = ["OEISSkill"]

logger = logging.getLogger(__name__)

_OEIS_SEARCH_URL = "https://oeis.org/search"


class OEISSkill(AsyncSkill):
    """Query the OEIS JSON API for integer-sequence records.

    Reads ``oeis_query`` from the context and writes ``oeis_results`` (a list
    of sequence record dicts as returned by the OEIS JSON endpoint).

    Config:
        max_results (int): Maximum number of sequences to return. Default: 10.
        timeout_seconds (int): HTTP request timeout. Default: 15.
    """

    skill_meta = SkillMeta(
        name="oeis",
        version="0.1.1",
        description="Query the On-Line Encyclopedia of Integer Sequences (OEIS)",
        provides=["oeis_results"],
        consumes=["oeis_query"],
        tags=["oeis", "mathematics", "sequences", "number-theory"],
        max_retries=2,
        retry_delay_base=1.0,
        retry_delay_max=30.0,
        config_schema={
            "type": "object",
            "properties": {
                "max_results": {"type": "integer"},
                "timeout_seconds": {"type": "integer"},
            },
        },
    )

    async def process(self, context: FlowContext) -> FlowContext:
        """Fetch matching OEIS sequences for the query in context.

        Args:
            context: Flow context; must contain ``oeis_query``.

        Returns:
            Updated context with ``oeis_results`` set.
        """
        query: str = context.get("oeis_query", "")
        if not query.strip():
            logger.warning("OEISSkill: 'oeis_query' is empty; skipping")
            context.set("oeis_results", [])
            return context

        max_results: int = int(self.config.get("max_results", 10))
        timeout: int = int(self.config.get("timeout_seconds", 15))

        results = await self._search_oeis(query.strip(), max_results, timeout)
        context.set("oeis_results", results)
        return context

    async def _search_oeis(
        self,
        query: str,
        max_results: int,
        timeout: int,
    ) -> list[dict[str, Any]]:
        """Issue a GET request to the OEIS JSON search endpoint.

        Args:
            query: Search query string.
            max_results: Maximum number of results to request.
            timeout: HTTP timeout in seconds.

        Returns:
            List of sequence record dicts, or an empty list on error.
        """
        params = {
            "q": query,
            "fmt": "json",
            "start": "0",
            "n": str(max_results),
        }
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(_OEIS_SEARCH_URL, params=params)
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                results: list[dict[str, Any]] = payload.get("results") or []
                logger.info(
                    "OEISSkill: query=%r returned %d result(s)", query, len(results)
                )
                return results
        except Exception as exc:
            logger.warning("OEISSkill: search failed for query=%r: %s", query, exc)
            return []
