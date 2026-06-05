#!/usr/bin/env python3
"""Tests for MCP compatibility entry points."""

from __future__ import annotations

import ast
from pathlib import Path


def test_root_mcp_server_is_thin_compatibility_wrapper() -> None:
    source = Path("mcp_server.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function_defs = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

    assert function_defs == []
    assert "from ate_smt7_diff.mcp.server import run_stdio" in source
    assert "run_stdio()" in source
