#!/usr/bin/env python3
"""Tests for MCP flow diff tools."""

from __future__ import annotations

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.mcp.cache import McpCache
from ate_smt7_diff.mcp.tools.diff import (
    diff_flows,
    export_diff_report,
    query_diff_report,
    register_diff_tools,
)


def _write_flow(path, suites: list[str]) -> None:
    body = "\n".join(f"run({suite});" for suite in suites)
    path.write_text(f"test_flow\n{body}\nend\n", encoding="utf-8")


def test_query_diff_report_cache_miss(tmp_path) -> None:
    cache = McpCache()
    old_flow = tmp_path / "old.flow"
    new_flow = tmp_path / "new.flow"
    _write_flow(old_flow, ["S1"])
    _write_flow(new_flow, ["S1"])

    payload = json.loads(query_diff_report(cache, str(old_flow), str(new_flow)))

    assert payload == {"error": "Report not found in cache. Run diff_flows first."}


def test_diff_flows_caches_single_report_and_query_returns_summary(tmp_path) -> None:
    cache = McpCache()
    old_flow = tmp_path / "old.flow"
    new_flow = tmp_path / "new.flow"
    _write_flow(old_flow, ["S1"])
    _write_flow(new_flow, ["S1", "S2"])

    diff_payload = json.loads(diff_flows(cache, str(old_flow), str(new_flow)))
    query_payload = json.loads(query_diff_report(cache, str(old_flow), str(new_flow)))

    assert diff_payload["added_tests"] == ["S2"]
    assert query_payload["added"] == ["S2"]
    assert query_payload["removed"] == []
    assert query_payload["order_changed"] == []


def test_diff_flows_rejects_non_flow_file(tmp_path) -> None:
    cache = McpCache()
    old_flow = tmp_path / "old.txt"
    new_flow = tmp_path / "new.flow"
    old_flow.write_text("not a flow", encoding="utf-8")
    _write_flow(new_flow, ["S1"])

    payload = json.loads(diff_flows(cache, str(old_flow), str(new_flow)))

    assert payload == {"error": f"Expected .flow file: {old_flow}"}


def test_export_diff_report_supports_markdown_after_diff(tmp_path) -> None:
    cache = McpCache()
    old_flow = tmp_path / "old.flow"
    new_flow = tmp_path / "new.flow"
    _write_flow(old_flow, ["S1"])
    _write_flow(new_flow, ["S1", "S2"])

    diff_flows(cache, str(old_flow), str(new_flow))
    markdown = export_diff_report(cache, str(old_flow), str(new_flow), format="markdown")

    assert "S2" in markdown


def test_register_diff_tools_adds_expected_tool_names() -> None:
    mcp = FastMCP("test")
    cache = McpCache()

    register_diff_tools(mcp, cache)

    async def names() -> list[str]:
        return sorted(tool.name for tool in await mcp.list_tools())

    assert asyncio.run(names()) == [
        "diff_flows",
        "export_diff_report",
        "query_diff_report",
    ]
