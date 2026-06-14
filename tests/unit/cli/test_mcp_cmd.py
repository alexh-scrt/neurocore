"""Tests for the `neurocore mcp` CLI group."""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from typer.testing import CliRunner

from neurocore.cli.app import app

runner = CliRunner()

pytest.importorskip("neurocore_skill_mcp")


class _Tool:
    def __init__(self, name: str, desc: str) -> None:
        self.name = name
        self.description = desc


class _ToolsResult:
    def __init__(self, tools: list[_Tool]) -> None:
        self.tools = tools


class _Session:
    async def list_tools(self) -> _ToolsResult:
        return _ToolsResult([_Tool("create_issue", "Create a GitHub issue")])


def test_list_tools_requires_command_or_url():
    result = runner.invoke(app, ["mcp", "list-tools"])
    assert result.exit_code != 0


def test_list_tools_happy_path(monkeypatch):
    @asynccontextmanager
    async def fake_open_session(cfg):
        yield _Session()

    import neurocore_skill_mcp.client as client_mod

    monkeypatch.setattr(client_mod, "open_session", fake_open_session)
    result = runner.invoke(app, ["mcp", "list-tools", "--command", "echo"])
    assert result.exit_code == 0, result.output
    assert "create_issue" in result.output


def test_list_tools_failure_is_graceful(monkeypatch):
    @asynccontextmanager
    async def boom(cfg):
        raise RuntimeError("no server")
        yield  # pragma: no cover

    import neurocore_skill_mcp.client as client_mod

    monkeypatch.setattr(client_mod, "open_session", boom)
    result = runner.invoke(app, ["mcp", "list-tools", "--command", "echo"])
    assert result.exit_code != 0
    assert "Failed to list tools" in result.output
