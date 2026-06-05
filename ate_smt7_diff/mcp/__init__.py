#!/usr/bin/env python3
"""MCP integration package for ate-smt7-diff."""

from ate_smt7_diff.mcp.cache import McpCache, cache_key
from ate_smt7_diff.mcp.server import create_server, run_stdio

__all__ = ["McpCache", "cache_key", "create_server", "run_stdio"]
