#!/usr/bin/env python3
"""Compatibility wrapper for the modular ate-smt7-diff MCP server."""

from __future__ import annotations

from ate_smt7_diff.mcp.server import run_stdio

if __name__ == "__main__":
    run_stdio()
