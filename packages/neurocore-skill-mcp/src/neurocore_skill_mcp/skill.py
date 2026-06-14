"""McpToolSkill — invoke a tool exposed by an MCP server.

Connects to an MCP server (stdio or streamable HTTP), calls a named tool with
merged static + runtime arguments, and writes the normalized result to context.

Config (flattened — NeuroCore validates only top-level keys):
    transport : "stdio" (default) | "http"
    command, args, env : stdio transport
    url, headers : http transport
    tool : name of the tool to invoke (required)
    arguments : static arguments dict (merged under runtime ``mcp_arguments``)
    result_key : context key to write (default "mcp_result")
"""
from __future__ import annotations

import logging
from typing import Any

from flowengine import FlowContext

from neurocore import AsyncSkill, SkillMeta

logger = logging.getLogger(__name__)


def _as_dict(value: Any) -> dict[str, Any]:
    """Coerce a config/context value (plain dict or flowengine DotDict) to a dict."""
    if not value:
        return {}
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return dict(to_dict())
    return dict(value)


class McpToolSkill(AsyncSkill):
    """Async skill that invokes an MCP server tool."""

    skill_meta = SkillMeta(
        name="mcp-tool",
        version="0.1.0",
        description="Invoke a tool exposed by an MCP server (stdio or streamable HTTP).",
        author="NeuroCore Contributors",
        requires=["mcp>=1.20"],
        provides=["mcp_result"],
        consumes=["mcp_arguments"],
        tags=["mcp", "tool", "interop"],
        max_retries=2,
        retry_delay_base=1.0,
        config_schema={
            "required": ["tool"],
            "properties": {
                "transport": {"type": "string", "enum": ["stdio", "http"]},
                "command": {"type": "string"},
                "args": {"type": "array", "items": {"type": "string"}},
                "env": {"type": "object"},
                "url": {"type": "string"},
                "headers": {"type": "object"},
                "tool": {"type": "string"},
                "arguments": {"type": "object"},
                "result_key": {"type": "string"},
            },
        },
    )

    async def process(self, context: FlowContext) -> FlowContext:
        result_key = self.config.get("result_key", "mcp_result")
        tool = self.config["tool"]
        static_args = _as_dict(self.config.get("arguments"))
        runtime_args = _as_dict(context.get("mcp_arguments"))
        call_args = {**static_args, **runtime_args}  # runtime overrides static

        from neurocore_skill_mcp.client import normalize_content, open_session

        try:
            async with open_session(self.config) as session:
                response = await session.call_tool(tool, call_args)
            context.set(result_key, normalize_content(response))
        except Exception as exc:  # noqa: BLE001
            logger.error("mcp-tool %r failed: %s", tool, exc, exc_info=True)
            context.set(result_key, {"error": str(exc)})
        return context
