#!/usr/bin/env python3
"""Tests for MCP agent-helper tools."""

from __future__ import annotations

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.mcp.cache import McpCache
from ate_smt7_diff.mcp.tools.agent import (
    register_agent_tools,
    smart_diff_discover,
    smart_diff_explain,
    smart_diff_suggest,
    smart_diff_validate,
)


def test_agent_tools_return_cache_miss_before_discovery() -> None:
    cache = McpCache()

    assert json.loads(smart_diff_suggest(cache, "old", "new")) == {
        "error": "Discovery result not found. Run smart_diff_discover first."
    }
    assert json.loads(smart_diff_explain(cache, "old", "new")) == {
        "error": "Discovery result not found. Run smart_diff_discover first."
    }
    assert json.loads(smart_diff_validate(cache, "old", "new")) == {
        "error": "Discovery result not found. Run smart_diff_discover first."
    }


def test_discover_populates_cache_and_follow_up_tools_return_json() -> None:
    cache = McpCache()
    old_package = "Test1/example1"
    new_package = "Test2/example2"

    discover_payload = json.loads(
        smart_diff_discover(cache, old_package, new_package, load_configs=False)
    )
    suggest_payload = json.loads(smart_diff_suggest(cache, old_package, new_package))
    explain_payload = json.loads(smart_diff_explain(cache, old_package, new_package))
    validate_payload = json.loads(smart_diff_validate(cache, old_package, new_package))

    assert discover_payload["old_package"].endswith("Test1/example1")
    assert discover_payload["new_package"].endswith("Test2/example2")
    assert "suggestions" in suggest_payload
    assert "explanations" in explain_payload
    assert "passed" in validate_payload
    assert "findings" in validate_payload


def test_register_agent_tools_adds_expected_tool_names() -> None:
    mcp = FastMCP("test")
    cache = McpCache()

    register_agent_tools(mcp, cache)

    async def names() -> list[str]:
        return sorted(tool.name for tool in await mcp.list_tools())

    assert asyncio.run(names()) == [
        "smart_diff_discover",
        "smart_diff_explain",
        "smart_diff_suggest",
        "smart_diff_validate",
    ]
