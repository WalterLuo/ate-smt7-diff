#!/usr/bin/env python3
"""FastMCP server assembly for ate-smt7-diff."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ate_smt7_diff.mcp.cache import McpCache
from ate_smt7_diff.mcp.resources import register_resources
from ate_smt7_diff.mcp.tools.agent import register_agent_tools
from ate_smt7_diff.mcp.tools.diff import register_diff_tools
from ate_smt7_diff.mcp.tools.packages import register_package_tools

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def create_server(cache: McpCache | None = None) -> FastMCP:
    """Create and configure the ate-smt7-diff MCP server."""
    state = cache or McpCache()
    mcp = FastMCP("ate-smt7-diff")
    register_package_tools(mcp)
    register_diff_tools(mcp, state)
    register_agent_tools(mcp, state)
    register_resources(mcp)
    return mcp


def run_stdio() -> None:
    """Run the MCP server using the local stdio transport."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    run_stdio()
