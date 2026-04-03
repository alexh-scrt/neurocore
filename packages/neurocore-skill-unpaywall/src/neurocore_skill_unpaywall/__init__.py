"""NeuroCore skill for fetching open-access PDF URLs via the Unpaywall API.

Given a list of DOIs in the FlowContext, this skill concurrently queries the
Unpaywall REST API and populates ``unpaywall_results`` with a mapping of
``{doi: pdf_url | None}``.

Configuration keys (set via ``skill.init(config)``)::

    email           (str, required) – registered e-mail for Unpaywall API
    timeout_seconds (int, default 10) – per-request HTTP timeout

Context keys consumed:

    dois – list[str]

Context keys provided:

    unpaywall_results – dict[str, str | None]
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

__all__ = ["UnpaywallSkill"]

logger = logging.getLogger(__name__)

_UNPAYWALL_BASE = "https://api.unpaywall.org/v2"


class UnpaywallSkill(AsyncSkill):
    """Fetch open-access PDF URLs from Unpaywall for a list of DOIs.

    Reads ``dois`` (``list[str]``) from the context, issues one HTTP GET per
    DOI concurrently, and writes ``unpaywall_results`` (``dict[str, str |
    None]``) back to the context.  Values are the best open-access PDF URL
    found by Unpaywall, or ``None`` when no OA version exists or an error
    occurs.

    Config:
        email (str, required): E-mail address required by the Unpaywall API.
        timeout_seconds (int): HTTP timeout per request. Default: 10.
    """

    skill_meta = SkillMeta(
        name="unpaywall",
        version="0.1.0",
        description="Fetch open-access PDF URLs from Unpaywall for a list of DOIs",
        provides=["unpaywall_results"],
        consumes=["dois"],
        tags=["literature", "open-access", "doi", "unpaywall"],
        config_schema={
            "type": "object",
            "required": ["email"],
            "properties": {
                "email": {"type": "string"},
                "timeout_seconds": {"type": "integer"},
            },
        },
    )

    async def process(self, context: FlowContext) -> FlowContext:
        """Query Unpaywall for each DOI concurrently.

        Args:
            context: The current flow context.  Must contain ``dois``.

        Returns:
            The same context with ``unpaywall_results`` populated.
        """
        dois: list[str] = context.get("dois", [])
        if not dois:
            logger.warning("UnpaywallSkill: no 'dois' found in context; skipping")
            context.set("unpaywall_results", {})
            return context

        email: str = self.config.get("email", "")
        timeout: int = int(self.config.get("timeout_seconds", 10))

        async with httpx.AsyncClient(timeout=timeout) as client:
            tasks = [self._fetch_doi(client, doi, email) for doi in dois]
            pairs: list[tuple[str, str | None]] = await asyncio.gather(*tasks)

        results: dict[str, str | None] = dict(pairs)
        context.set("unpaywall_results", results)
        return context

    async def _fetch_doi(
        self,
        client: httpx.AsyncClient,
        doi: str,
        email: str,
    ) -> tuple[str, str | None]:
        """Fetch the best OA PDF URL for a single DOI.

        Args:
            client: Shared async HTTP client.
            doi: The DOI string (e.g. ``"10.1038/nature12373"``).
            email: Registered e-mail for the Unpaywall API.

        Returns:
            A ``(doi, pdf_url | None)`` tuple.  Never raises.
        """
        url = f"{_UNPAYWALL_BASE}/{doi}"
        params = {"email": email}
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            pdf_url: str | None = data.get("best_oa_location", {}) or {}
            if isinstance(pdf_url, dict):
                pdf_url = pdf_url.get("url_for_pdf") or pdf_url.get("url")
            return doi, pdf_url
        except Exception as exc:
            logger.warning("UnpaywallSkill: failed to fetch DOI %s: %s", doi, exc)
            return doi, None
