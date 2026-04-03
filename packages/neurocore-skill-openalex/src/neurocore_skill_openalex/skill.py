"""OpenAlex skill — query the OpenAlex Works API for academic papers.

OpenAlex is a fully open catalogue of scholarly works. The free, public API
requires no authentication but participates in the "polite pool" when a valid
email address is supplied via the ``mailto`` query parameter.

Usage example::

    from neurocore_skill_openalex import OpenAlexSkill

    # Configure via NeuroCore config YAML:
    #
    #   skills:
    #     openalex:
    #       per_page: 10
    #       filter: "type:article,open_access.is_oa:true"
    #       sort: "cited_by_count:desc"
    #       email: "researcher@example.org"
    #
    # The skill reads `openalex_query` from the FlowContext and writes
    # `openalex_works` back.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

logger = logging.getLogger(__name__)

_OPENALEX_WORKS_URL = "https://api.openalex.org/works"

# Default set of fields requested from the API.
_DEFAULT_SELECT: list[str] = [
    "id",
    "doi",
    "title",
    "abstract_inverted_index",
    "publication_date",
    "cited_by_count",
    "open_access",
    "best_oa_location",
    "authorships",
    "topics",
]


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruct a plain-text abstract from OpenAlex's inverted index format.

    OpenAlex stores abstracts as an inverted index mapping each word to the
    list of positions it occupies in the original text.  This helper reverses
    that mapping so callers receive a normal string.

    Args:
        inverted_index: Mapping of ``{word: [position, ...]}`` or ``None``.

    Returns:
        Reconstructed abstract string, or an empty string when the input is
        ``None`` or empty.
    """
    if not inverted_index:
        return ""
    max_pos = max(pos for positions in inverted_index.values() for pos in positions)
    words: list[str] = [""] * (max_pos + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words)


def _extract_work(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract the canonical work dict from a raw OpenAlex API response object.

    Args:
        raw: A single work object as returned by the OpenAlex API.

    Returns:
        A dict containing exactly the keys defined in the behaviour contract:
        ``id``, ``doi``, ``title``, ``abstract``, ``publication_date``,
        ``cited_by_count``, ``open_access``, ``best_oa_location``,
        ``authorships``, ``topics``.
    """
    return {
        "id": raw.get("id"),
        "doi": raw.get("doi"),
        "title": raw.get("title"),
        "abstract": _reconstruct_abstract(raw.get("abstract_inverted_index")),
        "publication_date": raw.get("publication_date"),
        "cited_by_count": raw.get("cited_by_count"),
        "open_access": raw.get("open_access"),
        "best_oa_location": raw.get("best_oa_location"),
        "authorships": raw.get("authorships", []),
        "topics": raw.get("topics", []),
    }


class OpenAlexSkill(AsyncSkill):
    """Async skill that queries the OpenAlex Works API.

    **Config keys** (all optional):

    ``per_page`` (int, default 25)
        Number of results to return per page.

    ``filter`` (str)
        OpenAlex filter string, e.g.
        ``"type:article,open_access.is_oa:true"``.

    ``sort`` (str, default ``"publication_date:desc"``)
        Sort order, e.g. ``"cited_by_count:desc"``.

    ``select`` (list[str])
        Fields to return.  Defaults to the canonical set defined in
        ``_DEFAULT_SELECT``.

    ``email`` (str)
        Contact e-mail sent as the ``mailto`` query parameter to join the
        OpenAlex "polite pool" and receive faster, more reliable responses.

    **Context keys consumed:**

    ``openalex_query`` (str)
        The search query.  Required — if absent or empty the skill sets
        ``openalex_works`` to ``[]`` and returns immediately.

    **Context keys produced:**

    ``openalex_works`` (list[dict])
        List of work dicts.  Each dict contains:
        ``id``, ``doi``, ``title``, ``abstract``, ``publication_date``,
        ``cited_by_count``, ``open_access``, ``best_oa_location``,
        ``authorships``, ``topics``.
        Set to ``[]`` on HTTP failure (the skill never raises).
    """

    skill_meta = SkillMeta(
        name="openalex",
        version="0.1.1",
        description="Query OpenAlex for papers, citation counts, and author info",
        provides=["openalex_works"],
        consumes=["openalex_query"],
        config_schema={
            "properties": {
                "per_page": {"type": "integer", "default": 25},
                "filter": {"type": "string"},
                "sort": {"type": "string", "default": "publication_date:desc"},
                "select": {"type": "array"},
                "email": {"type": "string"},
            }
        },
        requires=["httpx>=0.27"],
        tags=["search", "papers", "citations", "open-access"],
        max_retries=3,
        retry_delay_base=2.0,
        retry_delay_max=30.0,
    )

    async def process(self, context: FlowContext) -> FlowContext:
        """Query the OpenAlex Works API and write results to the context.

        Reads ``openalex_query`` from *context*, performs an async HTTP GET
        against ``https://api.openalex.org/works``, and writes a list of
        normalised work dicts to ``openalex_works``.

        The method **never raises**.  Any HTTP or network error is caught,
        logged at ``ERROR`` level, and ``openalex_works`` is set to ``[]``.

        Args:
            context: The current :class:`~flowengine.FlowContext`.

        Returns:
            The same *context* object, with ``openalex_works`` set.
        """
        query: str = context.get("openalex_query", "") or ""
        if not query.strip():
            logger.warning(
                "OpenAlexSkill: 'openalex_query' is empty — skipping API call."
            )
            context.set("openalex_works", [])
            return context

        params = self._build_params(query)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(_OPENALEX_WORKS_URL, params=params)
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "OpenAlexSkill: HTTP %s error for query %r: %s",
                exc.response.status_code,
                query,
                exc,
            )
            context.set("openalex_works", [])
            return context
        except httpx.RequestError as exc:
            logger.error(
                "OpenAlexSkill: Request error for query %r: %s",
                query,
                exc,
            )
            context.set("openalex_works", [])
            return context
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "OpenAlexSkill: Unexpected error for query %r: %s",
                query,
                exc,
            )
            context.set("openalex_works", [])
            return context

        raw_works: list[dict[str, Any]] = payload.get("results", [])
        works = [_extract_work(w) for w in raw_works]
        logger.info(
            "OpenAlexSkill: retrieved %d work(s) for query %r.",
            len(works),
            query,
        )
        context.set("openalex_works", works)
        return context

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_params(self, query: str) -> dict[str, Any]:
        """Build the query-parameter dict for the OpenAlex API request.

        Args:
            query: The search string from context.

        Returns:
            Dict of query parameters suitable for :func:`httpx.AsyncClient.get`.
        """
        per_page: int = self.config.get("per_page", 25)
        sort: str = self.config.get("sort", "publication_date:desc")
        filter_str: str | None = self.config.get("filter")
        select_fields: list[str] | None = self.config.get("select")
        email: str | None = self.config.get("email")

        params: dict[str, Any] = {
            "search": query,
            "per-page": per_page,
            "sort": sort,
        }

        if filter_str:
            params["filter"] = filter_str

        # Build the select list from config or use the default set that
        # includes all required output fields.
        fields_to_select: list[str] = select_fields if select_fields else list(_DEFAULT_SELECT)
        params["select"] = ",".join(fields_to_select)

        if email:
            params["mailto"] = email

        return params
