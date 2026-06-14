"""Tests for McpToolSkill — uses a mocked MCP session (no real SDK needed)."""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from flowengine import FlowContext

from neurocore_skill_mcp import McpToolSkill
from neurocore_skill_mcp.client import normalize_content


class _Block:
    def __init__(self, text: str) -> None:
        self.text = text


class _Response:
    def __init__(self, text: str = "ok", structured: dict | None = None) -> None:
        self.content = [_Block(text)]
        self.structuredContent = structured


class _FakeSession:
    def __init__(self, response: _Response) -> None:
        self._response = response
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, tool: str, args: dict):
        self.calls.append((tool, args))
        return self._response


def _patch_session(monkeypatch, session: _FakeSession) -> None:
    @asynccontextmanager
    async def fake_open_session(cfg):
        yield session

    monkeypatch.setattr(
        "neurocore_skill_mcp.client.open_session", fake_open_session
    )


def test_skill_meta():
    meta = McpToolSkill.skill_meta
    assert meta.name == "mcp-tool"
    assert "mcp_result" in meta.provides
    assert "mcp_arguments" in meta.consumes


def test_validate_config_requires_tool():
    skill = McpToolSkill()
    skill.init({})  # no 'tool'
    errors = skill.validate_config()
    assert any("tool" in e for e in errors)


async def test_process_calls_tool_and_sets_result(monkeypatch):
    session = _FakeSession(_Response(text="hello"))
    _patch_session(monkeypatch, session)
    skill = McpToolSkill()
    skill.init({"transport": "stdio", "command": "x", "tool": "say",
                "arguments": {"a": 1}})
    ctx = await skill.process(FlowContext())
    assert ctx.get("mcp_result") == "hello"
    assert session.calls == [("say", {"a": 1})]


async def test_runtime_args_override_static(monkeypatch):
    session = _FakeSession(_Response())
    _patch_session(monkeypatch, session)
    skill = McpToolSkill()
    skill.init({"command": "x", "tool": "t", "arguments": {"a": 1, "b": 2}})
    ctx = FlowContext()
    ctx.set("mcp_arguments", {"b": 99, "c": 3})
    await skill.process(ctx)
    tool, args = session.calls[0]
    assert args == {"a": 1, "b": 99, "c": 3}


async def test_custom_result_key(monkeypatch):
    _patch_session(monkeypatch, _FakeSession(_Response(text="v")))
    skill = McpToolSkill()
    skill.init({"command": "x", "tool": "t", "result_key": "out"})
    ctx = await skill.process(FlowContext())
    assert ctx.get("out") == "v"


async def test_error_path_writes_error_sentinel(monkeypatch):
    @asynccontextmanager
    async def boom(cfg):
        raise RuntimeError("connection refused")
        yield  # pragma: no cover

    monkeypatch.setattr("neurocore_skill_mcp.client.open_session", boom)
    skill = McpToolSkill()
    skill.init({"command": "x", "tool": "t"})
    ctx = await skill.process(FlowContext())
    result = ctx.get("mcp_result")
    # FlowContext may wrap dicts as DotDict; check membership/value, not type.
    assert "error" in result
    assert "connection refused" in result.get("error")


def test_normalize_content_prefers_structured():
    class R:
        structuredContent = {"k": "v"}
        content = [_Block("ignored")]

    assert normalize_content(R()) == {"k": "v"}


def test_normalize_content_single_text():
    assert normalize_content(_Response(text="just one")) == "just one"
