"""Registry of project templates for ``neurocore new``.

Each template is a full project tree under ``scaffold/templates/<dir_name>/``.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateSpec:
    """Metadata for a ``neurocore new`` project template."""

    name: str
    description: str
    dir_name: str
    requires_extras: tuple[str, ...] = ()  # e.g. ("local",) → pip install neurocore-ai[local]
    suggested_skills: tuple[str, ...] = field(default_factory=tuple)


TEMPLATES: dict[str, TemplateSpec] = {
    "rag-agent": TemplateSpec(
        name="rag-agent",
        description="Retrieval-augmented generation over a Qdrant vector store.",
        dir_name="rag-agent",
        suggested_skills=("neurocore-skill-qdrant",),
    ),
    "research-agent": TemplateSpec(
        name="research-agent",
        description="Multi-source research agent (web search + arXiv + summarize).",
        dir_name="research-agent",
        suggested_skills=("neurocore-skill-tavily", "neurocore-skill-arxiv"),
    ),
    "ollama-agent": TemplateSpec(
        name="ollama-agent",
        description="Local LLM agent via Ollama (OpenAI-compatible).",
        dir_name="ollama-agent",
        requires_extras=("local",),
    ),
    "multi-agent-debate": TemplateSpec(
        name="multi-agent-debate",
        description="Two agents debate; a judge decides (graph flow).",
        dir_name="multi-agent-debate",
    ),
    "tool-agent": TemplateSpec(
        name="tool-agent",
        description="Tool-calling agent that invokes an MCP server tool.",
        dir_name="tool-agent",
        suggested_skills=("neurocore-skill-mcp",),
    ),
}


def list_templates() -> list[TemplateSpec]:
    """Return all templates sorted by name."""
    return [TEMPLATES[k] for k in sorted(TEMPLATES)]


def get_template(name: str) -> TemplateSpec | None:
    """Return a template by name, or None if unknown."""
    return TEMPLATES.get(name)
