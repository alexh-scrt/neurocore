"""Connection helpers for MCP servers (stdio and streamable HTTP).

The ``mcp`` SDK is imported lazily inside :func:`open_session` so that merely
importing the skill (e.g. for discovery) does not require the SDK to be present.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any


@asynccontextmanager
async def open_session(cfg: dict[str, Any]) -> AsyncIterator[Any]:
    """Open an initialized MCP ``ClientSession`` for the configured transport.

    Config keys:
        transport: "stdio" (default) or "http"
        command, args, env: for stdio transport
        url, headers: for streamable HTTP transport
    """
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    transport = cfg.get("transport", "stdio")
    if transport == "http":
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client(
            cfg["url"], headers=cfg.get("headers") or None
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    elif transport == "stdio":
        params = StdioServerParameters(
            command=cfg["command"],
            args=list(cfg.get("args", [])),
            env=cfg.get("env") or None,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    else:
        raise ValueError(
            f"Unknown MCP transport {transport!r}. Expected 'stdio' or 'http'."
        )


def normalize_content(response: Any) -> Any:
    """Convert an MCP ``CallToolResult`` into plain JSON-serializable data."""
    # Prefer structured content when present.
    structured = getattr(response, "structuredContent", None)
    if structured:
        return structured
    parts: list[Any] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
            continue
        data = getattr(block, "data", None)
        if data is not None:
            parts.append(data)
    if len(parts) == 1:
        return parts[0]
    return parts
