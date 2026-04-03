"""NeuroCore skill for vector similarity search and upsert via Qdrant.

Supports two modes:

* **search** – reads ``qdrant_query_vector`` from context, performs a nearest-
  neighbour search, and writes ``qdrant_results`` as a list of
  ``{id, score, payload}`` dicts.
* **upsert** – reads ``qdrant_points`` (list of ``{id, vector, payload}``
  dicts) from context and bulk-upserts them into the configured collection.

Configuration keys (set via ``skill.init(config)``)::

    url        (str, required)  – Qdrant server URL
    api_key    (str)            – optional API key
    collection (str, required)  – collection name
    top_k      (int, default 5) – number of nearest neighbours to return
    mode       (str, default "search") – "search" | "upsert"
    filter     (dict)          – optional Qdrant filter payload

Context keys consumed (search mode):

    qdrant_query_vector – list[float]

Context keys provided (search mode):

    qdrant_results – list[dict]  (each: {id, score, payload})

Context keys consumed (upsert mode):

    qdrant_points – list[dict]  (each: {id, vector, payload})
"""

from __future__ import annotations

import logging
from typing import Any

from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

__all__ = ["QdrantSkill"]

logger = logging.getLogger(__name__)


class QdrantSkill(AsyncSkill):
    """Qdrant vector-store skill supporting search and upsert operations.

    Config:
        url (str, required): Qdrant server URL (e.g. ``"http://localhost:6333"``).
        api_key (str): Optional Qdrant cloud API key.
        collection (str, required): Target collection name.
        top_k (int): How many results to return in search mode. Default: 5.
        mode (str): ``"search"`` or ``"upsert"``. Default: ``"search"``.
        filter (dict): Optional Qdrant payload filter (JSON-serialisable).
    """

    skill_meta = SkillMeta(
        name="qdrant",
        version="0.1.1",
        description="Vector similarity search and upsert via Qdrant",
        provides=["qdrant_results"],
        consumes=["qdrant_query_vector", "qdrant_points"],
        tags=["vector-store", "search", "qdrant", "embeddings"],
        max_retries=3,
        retry_delay_base=2.0,
        retry_delay_max=30.0,
        config_schema={
            "type": "object",
            "required": ["url", "collection"],
            "properties": {
                "url": {"type": "string"},
                "api_key": {"type": "string"},
                "collection": {"type": "string"},
                "top_k": {"type": "integer"},
                "mode": {"type": "string", "enum": ["search", "upsert"]},
                "filter": {"type": "object"},
            },
        },
    )

    async def process(self, context: FlowContext) -> FlowContext:
        """Execute search or upsert against Qdrant.

        Args:
            context: The current flow context.

        Returns:
            Updated context with ``qdrant_results`` (search mode) populated.
        """
        try:
            from qdrant_client import AsyncQdrantClient
            from qdrant_client.models import PointStruct
        except ImportError as exc:  # pragma: no cover
            logger.error("QdrantSkill: qdrant-client is not installed: %s", exc)
            context.set("qdrant_results", [])
            return context

        url: str = self.config.get("url", "")
        api_key: str | None = self.config.get("api_key") or None
        collection: str = self.config.get("collection", "")
        top_k: int = int(self.config.get("top_k", 5))
        mode: str = self.config.get("mode", "search")
        filter_payload: dict[str, Any] | None = self.config.get("filter") or None

        if not url or not collection:
            logger.error("QdrantSkill: 'url' and 'collection' are required in config")
            context.set("qdrant_results", [])
            return context

        try:
            client = AsyncQdrantClient(url=url, api_key=api_key)
            if mode == "upsert":
                await self._upsert(client, collection, context, PointStruct)
            else:
                await self._search(client, collection, top_k, filter_payload, context)
            await client.close()
        except Exception as exc:
            logger.warning("QdrantSkill: operation failed: %s", exc)
            if mode == "search":
                context.set("qdrant_results", [])

        return context

    async def _search(
        self,
        client: Any,
        collection: str,
        top_k: int,
        filter_payload: dict[str, Any] | None,
        context: FlowContext,
    ) -> None:
        """Perform a nearest-neighbour search and store results in context.

        Args:
            client: Qdrant async client.
            collection: Collection name to query.
            top_k: Maximum number of results to return.
            filter_payload: Optional Qdrant filter dict.
            context: Flow context; ``qdrant_results`` will be set here.
        """
        query_vector: list[float] = context.get("qdrant_query_vector", [])
        if not query_vector:
            logger.warning("QdrantSkill: 'qdrant_query_vector' is empty; skipping search")
            context.set("qdrant_results", [])
            return

        from qdrant_client.models import Filter

        qdrant_filter: Filter | None = None
        if filter_payload:
            try:
                qdrant_filter = Filter(**filter_payload)
            except Exception as exc:
                logger.warning("QdrantSkill: invalid filter payload: %s", exc)

        hits = await client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        )
        results = [
            {"id": hit.id, "score": hit.score, "payload": hit.payload or {}}
            for hit in hits
        ]
        context.set("qdrant_results", results)

    async def _upsert(
        self,
        client: Any,
        collection: str,
        context: FlowContext,
        PointStruct: type,
    ) -> None:
        """Bulk-upsert points into a Qdrant collection.

        Args:
            client: Qdrant async client.
            collection: Target collection name.
            context: Flow context; must contain ``qdrant_points``.
            PointStruct: Qdrant PointStruct model class.
        """
        raw_points: list[dict[str, Any]] = context.get("qdrant_points", [])
        if not raw_points:
            logger.warning("QdrantSkill: 'qdrant_points' is empty; skipping upsert")
            return

        points = [
            PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload=p.get("payload", {}),
            )
            for p in raw_points
        ]
        await client.upsert(collection_name=collection, points=points)
        logger.info("QdrantSkill: upserted %d points into '%s'", len(points), collection)
