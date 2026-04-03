"""NeuroCore skill for full-text PDF extraction via GROBID.

GROBID (GeneRation Of BIbliographic Data) is a machine-learning library for
extracting, parsing, and re-structuring raw documents such as PDF into
structured TEI/XML.

This skill reads a PDF file path from the flow context, POSTs it to a running
GROBID server, and writes the resulting TEI XML string back to the context.

Configuration keys (set via ``skill.init(config)``)::

    grobid_url                (str, required) – base URL of the GROBID server
    consolidate_header        (int, default 1) – 0|1|2 consolidation level for header
    consolidate_citations     (int, default 0) – 0|1|2 consolidation level for citations
    include_raw_affiliations  (bool, default False) – include raw affiliation strings
    timeout_seconds           (int, default 60) – HTTP timeout for the upload

Context keys consumed:

    pdf_path – str  (absolute path to the PDF file)

Context keys provided:

    grobid_tei – str  (TEI XML returned by GROBID, or empty string on error)
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta

__all__ = ["GrobidSkill"]

logger = logging.getLogger(__name__)

_GROBID_ENDPOINT = "/api/processFulltextDocument"


class GrobidSkill(AsyncSkill):
    """Extract structured TEI XML from a PDF using a GROBID server.

    Reads ``pdf_path`` (``str``) from context, POSTs the PDF as multipart
    form data to ``{grobid_url}/api/processFulltextDocument``, and writes the
    TEI XML response to ``grobid_tei``.

    Config:
        grobid_url (str, required): Base URL of the GROBID instance.
        consolidate_header (int): Header consolidation level (0/1/2). Default: 1.
        consolidate_citations (int): Citation consolidation level (0/1/2). Default: 0.
        include_raw_affiliations (bool): Include raw affiliations. Default: False.
        timeout_seconds (int): HTTP request timeout in seconds. Default: 60.
    """

    skill_meta = SkillMeta(
        name="grobid",
        version="0.1.0",
        description="Extract structured TEI XML from a PDF via GROBID",
        provides=["grobid_tei"],
        consumes=["pdf_path"],
        tags=["pdf", "nlp", "grobid", "tei", "extraction"],
        config_schema={
            "type": "object",
            "required": ["grobid_url"],
            "properties": {
                "grobid_url": {"type": "string"},
                "consolidate_header": {"type": "integer"},
                "consolidate_citations": {"type": "integer"},
                "include_raw_affiliations": {"type": "boolean"},
                "timeout_seconds": {"type": "integer"},
            },
        },
    )

    async def process(self, context: FlowContext) -> FlowContext:
        """Send PDF to GROBID and store the resulting TEI XML.

        Args:
            context: Flow context; must contain ``pdf_path``.

        Returns:
            Updated context with ``grobid_tei`` set.
        """
        pdf_path_str: str = context.get("pdf_path", "")
        if not pdf_path_str:
            logger.warning("GrobidSkill: 'pdf_path' not found in context; skipping")
            context.set("grobid_tei", "")
            return context

        pdf_path = Path(pdf_path_str)
        if not pdf_path.exists():
            logger.warning("GrobidSkill: file not found at '%s'; skipping", pdf_path)
            context.set("grobid_tei", "")
            return context

        grobid_url: str = self.config.get("grobid_url", "").rstrip("/")
        consolidate_header: int = int(self.config.get("consolidate_header", 1))
        consolidate_citations: int = int(self.config.get("consolidate_citations", 0))
        include_raw_affiliations: bool = bool(
            self.config.get("include_raw_affiliations", False)
        )
        timeout: int = int(self.config.get("timeout_seconds", 60))

        endpoint = f"{grobid_url}{_GROBID_ENDPOINT}"

        try:
            tei_xml = await self._post_pdf(
                endpoint=endpoint,
                pdf_path=pdf_path,
                consolidate_header=consolidate_header,
                consolidate_citations=consolidate_citations,
                include_raw_affiliations=include_raw_affiliations,
                timeout=timeout,
            )
        except Exception as exc:
            logger.warning("GrobidSkill: extraction failed: %s", exc)
            tei_xml = ""

        context.set("grobid_tei", tei_xml)
        return context

    async def _post_pdf(
        self,
        endpoint: str,
        pdf_path: Path,
        consolidate_header: int,
        consolidate_citations: int,
        include_raw_affiliations: bool,
        timeout: int,
    ) -> str:
        """POST the PDF to GROBID and return the TEI XML string.

        Args:
            endpoint: Full URL to the GROBID processFulltextDocument endpoint.
            pdf_path: Path to the PDF file on disk.
            consolidate_header: Header consolidation level.
            consolidate_citations: Citation consolidation level.
            include_raw_affiliations: Whether to include raw affiliations.
            timeout: HTTP timeout in seconds.

        Returns:
            TEI XML string returned by GROBID.

        Raises:
            httpx.HTTPStatusError: On non-2xx HTTP responses.
            httpx.RequestError: On network-level errors.
        """
        data: dict[str, str] = {
            "consolidateHeader": str(consolidate_header),
            "consolidateCitations": str(consolidate_citations),
            "includeRawAffiliations": "1" if include_raw_affiliations else "0",
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            with pdf_path.open("rb") as fh:
                files = {"input": (pdf_path.name, fh, "application/pdf")}
                response = await client.post(endpoint, data=data, files=files)
            response.raise_for_status()
            return response.text
